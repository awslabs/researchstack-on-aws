# Cost Optimization Guide

## Understanding Research Computing Costs

AWS costs vary by region, usage patterns, and pricing changes. Instead of static estimates, focus on optimization strategies and tools to control costs.

### Cost Components
- **Compute**: EC2, SageMaker, ParallelCluster
- **Storage**: S3, EFS, EBS volumes
- **Networking**: Data transfer, NAT gateways
- **F&A Overhead**: Currently 50-70% at most institutions, but enacted law (P.L. 119-75, Feb 2026) directs OMB to exclude cloud from F&A — see [F&A and Cloud Computing](#fa-and-cloud-computing) below

## Cost Optimization Strategies

### Storage Optimization

**S3 Intelligent Tiering** (Automatic)
- Moves data between access tiers automatically
- No retrieval fees
- Saves 70-95% on infrequently accessed data
- **All templates use this by default**

**EFS Lifecycle Management**
- Moves files to Infrequent Access tier after 30 days
- Saves ~90% on inactive files
- Transparent to applications

**Delete Unused Resources**
- Old EBS snapshots
- Unused EBS volumes
- Abandoned S3 buckets

### Compute Optimization

**Stop Instances When Not in Use**
- SageMaker: Stop notebook instances between sessions
- EC2: Stop instances overnight/weekends
- Savings: 50-70% for intermittent workloads

**Use Spot Instances** (70% savings)
- ParallelCluster: Enable spot for compute nodes (already supported)
- Fault-tolerant workloads only
- **Note**: Current EC2 templates don't support spot - use ParallelCluster or see Phase 4 roadmap

**Right-Size Instances**
- Start small, scale up if needed
- Use AWS Compute Optimizer recommendations
- Monitor CPU/memory utilization

**Savings Plans** (Up to 72% savings)
- **Compute Savings Plans**: Most flexible - applies to EC2, Lambda, Fargate
- **EC2 Instance Savings Plans**: Higher discount but less flexible
- Commit to $/hour usage for 1 or 3 years
- Automatically applies to eligible usage
- **Recommended over Reserved Instances** for most research workloads

### Research Phase Strategies

**Phase 2A (Data Collection)**
- S3 Standard for active uploads
- Intelligent Tiering for long-term storage
- Minimal compute costs

**Phase 2B (Exploration)**
- Use spot instances where possible
- Stop instances when not in use
- Start with smaller instance types
- Delete failed experiments

**Phase 2C (Production)**
- Consider Savings Plans for stable workloads (more flexible than Reserved Instances)
- Use auto-scaling (ParallelCluster)
- Optimize data transfer patterns
- Schedule batch jobs for off-peak

**Phase 3 (Archival)**
- S3 Glacier Deep Archive (cheapest)
- Delete compute resources
- Keep only final results and raw data

### Networking Optimization

**Minimize Data Transfer**
- Keep compute and storage in same region
- Use VPC endpoints for S3 (free)
- Avoid unnecessary cross-region transfers

**NAT Gateway Alternatives**
- Use VPC endpoints instead where possible
- Consider NAT instances for low-traffic scenarios
- Or use public subnets with security groups

## Cost Tracking

### Required Tags (All Templates)
All templates enforce these tags for cost allocation:
- **Project**: Research project name
- **CostCenter**: Department or grant number
- **Owner**: PI or researcher email
- **ManagedBy**: ResearchStack
- **Environment**: Research

### Activating Cost Allocation Tags

AWS resources are tagged automatically by ResearchStack templates, but tags don't appear in Cost Explorer or Budgets until you activate them as **cost allocation tags** in the Billing console. This is a one-time setup per account (or per management account if using AWS Organizations).

1. Go to **Billing and Cost Management → Cost Allocation Tags** ([direct link](https://console.aws.amazon.com/billing/home#/tags))
2. Find the tags: `Project`, `CostCenter`, `Owner`, `ManagedBy`, `Environment`
3. Select them and click **Activate**
4. Wait 24 hours — activated tags take up to 24 hours before cost data starts appearing in Cost Explorer and Budgets. Tags only apply to costs incurred *after* activation (not retroactive).

If you're using AWS Organizations, activate tags in the **management account** — this enables them across all member accounts. Individual member accounts cannot activate cost allocation tags independently.

Without this step, tag-based budget filtering and Cost Explorer breakdowns won't work, even though the tags exist on the resources.

### Cost Allocation Reports
1. Activate cost allocation tags (see above)
2. Use AWS Cost Explorer to filter by tags
3. Create monthly reports by Project/CostCenter
4. Add F&A overhead for grant reporting (if your institution still applies it to cloud — see note above about P.L. 119-75)

### Budget Alerts

Use the **Budget Alert** template (`templates/governance/budget-alert.yaml`) to create automated budget tracking per cost center. The template:
- Creates a monthly budget filtered by your `CostCenter` tag (optionally narrowed to a specific `Project`)
- Sends email alerts at 50% (actual), 80% (actual), and 100% (forecasted) of your budget

Deploy via Service Catalog or CloudFormation:
```bash
aws cloudformation create-stack \
  --stack-name grant-12345-budget \
  --template-body file://templates/governance/budget-alert.yaml \
  --parameters \
    ParameterKey=BudgetName,ParameterValue=grant-12345-monthly \
    ParameterKey=BudgetAmountUSD,ParameterValue=5000 \
    ParameterKey=CostCenter,ParameterValue=grant-12345 \
    ParameterKey=NotificationEmail,ParameterValue=pi@university.edu
```

For per-instance cost enforcement (automatically stopping an EC2 instance when its budget is exceeded), this feature is planned for EC2 templates — see the project roadmap.

Note: AWS Budgets evaluates cost data with a 12-24 hour lag. Budget alerts and enforcement are safety nets, not real-time spending caps.

## F&A and Cloud Computing

Historically, most U.S. research institutions classify cloud computing as a "service" in the Modified Total Direct Cost (MTDC) base, which means the full negotiated F&A rate (typically 50-70% at R1 institutions) is applied to every dollar of cloud spending on a federal grant. A researcher spending $500,000 on cloud at a 60% F&A rate must budget an additional $300,000 in indirect costs. By contrast, on-premises hardware purchases over $5,000 qualify as "equipment" and are excluded from MTDC — no F&A is charged.

This is changing. The Consolidated Appropriations Act, 2026 ([P.L. 119-75](https://www.congress.gov/bill/119th-congress/house-bill/7148)), signed by President Trump on February 3, 2026, directs the OMB Director to "clarify that technology investments, whether for hardware or cloud computing, procured in support of projects funded by Federal grants should be subject to the same cost treatment and not subject to Facilities and Administration costs." This language has the force of law.

Once OMB publishes the clarification, cloud costs on federal grants will carry zero F&A — the same treatment as equipment purchases. The timing of OMB action is uncertain, but the direction is enacted and bipartisan (identical language appeared in FY2025 appropriations and the FY2025 NDAA before being enacted in FY2026).

For grant budgeting: check with your grants office for your institution's current F&A treatment of cloud, but model multi-year budgets with the expectation that F&A on cloud is being eliminated.

## Cost Estimation Tools

**AWS Pricing Calculator**
- https://calculator.aws.amazon.com/
- Estimate costs before deployment
- Export estimates for grant proposals
- Remember to check whether F&A applies to cloud at your institution (see Cost Components above)

**AWS Cost Explorer**
- Track actual spending
- Identify cost trends
- Find optimization opportunities
- Filter by tags for chargeback

**AWS Compute Optimizer**
- Right-sizing recommendations
- Based on actual usage patterns
- Free service

## Common Cost Pitfalls

1. **Leaving instances running 24/7** - Stop when not in use
2. **Not using S3 Intelligent Tiering** - All templates use this
3. **Ignoring data transfer costs** - Keep data and compute in same region
4. **Not deleting failed experiments** - Clean up regularly
5. **Over-provisioning** - Start small, scale up as needed
6. **Not monitoring costs** - Set up budget alerts

## Grant Budgeting Tips

1. Use AWS Pricing Calculator for initial estimates
2. Add 20-30% buffer for usage variability
3. Include F&A overhead if your institution still applies it to cloud — but note that P.L. 119-75 (Feb 2026) directs OMB to exclude cloud from F&A, matching on-premises equipment treatment. Model accordingly.
4. Plan for data egress costs if sharing data
5. Consider Savings Plans for multi-year grants (up to 72% savings)
6. Document cost optimization strategies in proposal
7. Savings Plans are more flexible than Reserved Instances for research workloads
