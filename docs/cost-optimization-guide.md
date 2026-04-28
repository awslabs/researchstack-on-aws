# Cost Optimization Guide

## Understanding Research Computing Costs

AWS costs vary by region, usage patterns, and pricing changes. Instead of static estimates, focus on optimization strategies and tools to control costs.

### Cost Components
- **Compute**: [EC2](https://aws.amazon.com/ec2/pricing/), [SageMaker](https://aws.amazon.com/sagemaker/pricing/), [ParallelCluster](https://aws.amazon.com/hpc/parallelcluster/) (uses EC2 pricing)
- **Storage**: [S3](https://aws.amazon.com/s3/pricing/), [EFS](https://aws.amazon.com/efs/pricing/), [EBS volumes](https://aws.amazon.com/ebs/pricing/)
- **Networking**: [Data transfer](https://aws.amazon.com/ec2/pricing/on-demand/#Data_Transfer), [NAT gateways](https://aws.amazon.com/vpc/pricing/)
- **F&A Overhead**: Currently 50-70% at most institutions, but enacted law (P.L. 119-75, Feb 2026) directs OMB to exclude cloud from F&A — see [F&A and Cloud Computing](#fa-and-cloud-computing) below

## Cost Optimization Strategies

Cost optimization matters at every phase of the research lifecycle — from choosing the right instance size during exploration to archiving data after publication. Small decisions compound: an idle instance left running over a weekend costs the same as a week of active use. See the [Research Lifecycle Guide](research-lifecycle-guide.md) for how templates map to each research phase.

### Storage Optimization

**S3 Intelligent Tiering** (Automatic)
- Moves data between access tiers automatically based on usage patterns — frequently accessed data stays in a fast tier, infrequently accessed data moves to cheaper tiers
- No retrieval fees — even for data that moves to the archive tiers within Intelligent Tiering (unlike [S3 Glacier](https://aws.amazon.com/s3/storage-classes/glacier/), which charges per retrieval request)
- Saves 70-95% on infrequently accessed data
- **All ResearchStack S3 templates use this by default**

**EFS Lifecycle Management**
- Moves files not accessed for 30 days to the Infrequent Access tier (~$0.016/GB vs ~$0.30/GB for Standard)
- Saves ~90% on inactive files
- Transparent to applications — files move back to Standard automatically on next access
- **The ResearchStack EFS template enables this by default** (`TransitionToIA: AFTER_30_DAYS`)

**S3 Files (Filesystem on S3)**
- Mount an S3 bucket as a POSIX filesystem — read/write files directly at ~$0.023/GB/month (~13x cheaper than EFS Standard)
- Best for single-instance workloads or read-heavy access patterns
- EC2 templates default to auto-creating S3 Files storage — no extra setup needed
- Use EFS instead when multiple instances need concurrent write access to the same files

**Delete Unused Resources**
- Old [EBS snapshots](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html) (charged per GB stored)
- Unused EBS volumes (charged even when not attached to an instance)
- Abandoned S3 buckets and EFS volumes

### Compute Optimization

**Stop Instances When Not in Use**
- **SageMaker**: SageMaker Studio apps (JupyterLab, Code Editor) auto-stop when idle — compute only runs during active sessions, training jobs, or inference. No manual action needed for most workloads.
- **EC2**: ResearchStack EC2 templates include an idle shutdown feature that automatically stops instances when CPU utilization stays below 5% for a configurable period (default: 120 minutes). This catches the common case of a researcher finishing for the day and forgetting to stop the instance. You can disable it or adjust the duration via template parameters.
- **ParallelCluster**: Compute nodes auto-terminate after idle timeout (default: 10 minutes). The head node stays running — stop it manually via the EC2 console or CLI when the cluster isn't in use.
- Savings: 50-70% for intermittent workloads

**Use Spot Instances** (up to 70% savings)
- [Spot Instances](https://aws.amazon.com/ec2/spot/) use spare EC2 capacity at a steep discount, but AWS can reclaim them with 2 minutes notice. Use for fault-tolerant workloads only — batch jobs, training runs with checkpointing, or any work that can be interrupted and restarted.
- EC2 templates: set `PricingModel` to `spot` — instance stops (not terminates) on interruption, preserving your data
- Spot Fleet template (`ec2-spot-fleet.yaml`): spreads across multiple instance types and AZs for better availability
- ParallelCluster: set `ComputePricingModel` to `SPOT` — Slurm automatically requeues interrupted jobs
- Not recommended for: interactive sessions, long-running simulations without checkpointing, or anything where interruption means lost work

**Right-Size Instances**
- Start small (e.g., `m7i.xlarge`), scale up if CPU or memory is consistently maxed out
- Use [AWS Compute Optimizer](https://aws.amazon.com/compute-optimizer/) for right-sizing recommendations based on actual usage patterns (free service, no setup required — just enable it in the [Compute Optimizer console](https://console.aws.amazon.com/compute-optimizer/))
- Monitor CPU/memory utilization in [CloudWatch](https://console.aws.amazon.com/cloudwatch/) — if utilization is consistently below 30%, you're likely over-provisioned

**Savings Plans** (up to 72% savings)
- [Savings Plans](https://aws.amazon.com/savingsplans/) offer significant discounts in exchange for committing to a consistent amount of compute usage (measured in $/hour) for 1 or 3 years. Two types:
  - **Compute Savings Plans**: Most flexible — discounts apply automatically to any EC2 instance (any family, size, OS, region), Lambda, and Fargate usage. Best for research workloads where instance types change frequently.
  - **EC2 Instance Savings Plans**: Higher discount (up to 72%) but locked to a specific instance family and region. Best for stable, predictable workloads that won't change instance types.
- Discounts apply automatically to eligible usage — no code changes or tagging needed
- Use the [Savings Plans estimator](https://aws.amazon.com/savingsplans/compute-pricing/) to model costs based on your historical usage
- **Recommended over Reserved Instances** for most research workloads — Savings Plans are more flexible and easier to manage

### Research Phase Strategies

Cost optimization isn't a one-time activity — it should be considered at every phase of the research lifecycle. Different phases have different cost profiles, and the strategies that save money during exploration are different from those that matter in production. For a full mapping of research phases to templates, see the [Research Lifecycle Guide](research-lifecycle-guide.md).

**Phase 2A (Data Collection)**
- Use [S3 Standard](https://aws.amazon.com/s3/storage-classes/) for active uploads — data is immediately accessible
- Intelligent Tiering handles long-term storage automatically (no manual tier management)
- Minimal compute costs — data ingestion is typically lightweight

**Phase 2B (Exploration)**
- Use [Spot Instances](https://aws.amazon.com/ec2/spot/) for fault-tolerant experimentation (up to 70% savings) — if a job gets interrupted, just rerun it
- Idle shutdown (enabled by default on EC2 templates) catches forgotten instances
- Start with smaller instance types and scale up only if needed — exploration rarely needs the largest instances
- Delete failed experiments and their resources promptly — unused EBS volumes and snapshots accumulate cost silently

**Phase 2C (Production)**
- Consider [Savings Plans](https://aws.amazon.com/savingsplans/) for stable, predictable workloads running months or longer — the 1-year commitment typically breaks even around 7-9 months, so short-term projects won't benefit
- Use ParallelCluster auto-scaling — compute nodes launch on job submission and terminate when idle, so you only pay for active computation
- Keep compute and data in the same region to minimize [data transfer costs](https://aws.amazon.com/ec2/pricing/on-demand/#Data_Transfer)
- Schedule batch jobs during off-peak hours if your workload is flexible — spot pricing is often lower overnight and on weekends

**Phase 3 (Archival)**
- Move final datasets to [S3 Glacier Deep Archive](https://aws.amazon.com/s3/storage-classes/glacier/) (~$0.00099/GB/month — the cheapest storage option)
- Delete all compute resources (EC2 instances, ParallelCluster stacks, SageMaker domains)
- Keep only final results and raw data — intermediate outputs can be regenerated if needed

### Networking Optimization

**Minimize Data Transfer**
- Keep compute and storage in the same AWS region — [cross-region data transfer](https://aws.amazon.com/ec2/pricing/on-demand/#Data_Transfer) is charged per GB
- Use [VPC endpoints for S3](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html) (free, included in the Research VPC template) — traffic stays on the AWS network instead of going through the NAT gateway
- Avoid unnecessary cross-region transfers — if your data is in `us-east-1`, run your compute there too

**NAT Gateway Costs**
- NAT gateways have a base cost (~$32/month) plus per-GB data processing charges
- The Research VPC template includes a NAT gateway for private subnet internet access
- To reduce costs: use [VPC endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html) for AWS services (S3, DynamoDB endpoints are free), and delete the VPC stack when not in use

## Cost Tracking

### Required Tags (All Templates)
All ResearchStack templates automatically tag resources for cost allocation:
- **Project**: Research project name
- **CostCenter**: Department or grant number
- **Owner**: PI or researcher email
- **ManagedBy**: ResearchStack
- **Environment**: Research

These tags enable filtering in [Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/), [Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/), and [Data Exports](https://docs.aws.amazon.com/cur/latest/userguide/what-is-data-exports.html) for per-project and per-grant chargeback reporting.

### Activating Cost Allocation Tags

AWS resources are tagged automatically by ResearchStack templates, but tags don't appear in Cost Explorer or Budgets until you activate them as **cost allocation tags** in the Billing console. This is a one-time setup per account (or per management account if using AWS Organizations).

1. Go to **Billing and Cost Management → Cost Allocation Tags** ([direct link](https://console.aws.amazon.com/billing/home#/tags))
2. Find the tags: `Project`, `CostCenter`, `Owner`, `ManagedBy`, `Environment`
3. Select them and click **Activate**
4. Wait 24 hours — activated tags take up to 24 hours before cost data starts appearing in Cost Explorer and Budgets. Tags only apply to costs incurred *after* activation (not retroactive).

If you're using AWS Organizations, activate tags in the **management account** — this enables them across all member accounts. Individual member accounts cannot activate cost allocation tags independently.

Without this step, tag-based budget filtering and Cost Explorer breakdowns won't work, even though the tags exist on the resources.

### Cost Reporting

For day-to-day cost visibility, use [AWS Cost Explorer](https://console.aws.amazon.com/cost-management/home#/cost-explorer) — filter by `CostCenter` or `Project` tags to see spending per grant or research activity.

For detailed chargeback reporting, grant reconciliation, or integration with institutional finance systems, set up [AWS Data Exports](https://docs.aws.amazon.com/cur/latest/userguide/what-is-data-exports.html). Data Exports delivers detailed cost and usage data (hourly granularity, per-resource breakdowns) to an S3 bucket on a recurring schedule. From there, you can query it with [Amazon Athena](https://aws.amazon.com/athena/) or visualize it in [Amazon QuickSight](https://aws.amazon.com/quicksight/). This is the AWS-recommended approach for institutional cost reporting — it replaces the legacy Cost and Usage Reports (CUR).

For organizations managing multiple accounts, [Cloud Intelligence Dashboards](https://docs.aws.amazon.com/guidance/latest/cloud-intelligence-dashboards/getting-started.html) provide pre-built QuickSight dashboards on top of Data Exports — including cost breakdowns by account, service, tag, and usage type. They simplify cross-organization cost visibility without building dashboards from scratch.

### Budget Alerts

Use the **Budget Alert** template (`templates/governance/budget-alert.yaml`) to create automated budget tracking per cost center. The template:
- Creates a monthly budget filtered by your `CostCenter` tag (optionally narrowed to a specific `Project`)
- Sends email alerts at 50% (actual), 80% (actual), 100% (forecasted), and 100% (actual) of your budget

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

Note: AWS Budgets evaluates cost data with a 12-24 hour lag. Budget alerts are safety nets, not real-time spending caps.

For Service Catalog deployments, you can also enforce valid cost center values at provisioning time using [TagOptions](service-catalog-guide.md#enforcing-tag-values-with-tagoptions) — researchers select from a dropdown instead of typing free text.

## F&A and Cloud Computing

Historically, most U.S. research institutions classify cloud computing as a "service" in the Modified Total Direct Cost (MTDC) base, which means the full negotiated F&A rate (typically 50-70% at R1 institutions) is applied to every dollar of cloud spending on a federal grant. A researcher spending $500,000 on cloud at a 60% F&A rate must budget an additional $300,000 in indirect costs. By contrast, on-premises hardware purchases over $5,000 qualify as "equipment" and are excluded from MTDC — no F&A is charged.

This is changing. The Consolidated Appropriations Act, 2026 ([P.L. 119-75](https://www.congress.gov/bill/119th-congress/house-bill/7148)), signed by President Trump on February 3, 2026, directs the OMB Director to "clarify that technology investments, whether for hardware or cloud computing, procured in support of projects funded by Federal grants should be subject to the same cost treatment and not subject to Facilities and Administration costs." This language has the force of law.

Once OMB publishes the clarification, cloud costs on federal grants will carry zero F&A — the same treatment as equipment purchases. The timing of OMB action is uncertain, but the direction is enacted and bipartisan (identical language appeared in FY2025 appropriations and the FY2025 NDAA before being enacted in FY2026).

For grant budgeting: check with your grants office for your institution's current F&A treatment of cloud, but model multi-year budgets with the expectation that F&A on cloud is being eliminated.

## Cost Estimation Tools

**[AWS Pricing Calculator](https://calculator.aws/)**
- Estimate costs before deployment — model instance types, storage, and data transfer
- Export estimates as PDF or CSV for grant proposals

**[AWS Cost Explorer](https://console.aws.amazon.com/cost-management/home#/cost-explorer)**
- Track actual spending in real time
- Identify cost trends and anomalies
- Filter by tags (`CostCenter`, `Project`) for per-grant visibility
- Available in the [Billing and Cost Management console](https://console.aws.amazon.com/cost-management/)

**[AWS Compute Optimizer](https://console.aws.amazon.com/compute-optimizer/)**
- Right-sizing recommendations based on actual CPU, memory, and network utilization
- Identifies over-provisioned and under-provisioned instances
- Free service — just [enable it](https://docs.aws.amazon.com/compute-optimizer/latest/ug/getting-started.html) in the console

## Common Cost Pitfalls

1. **Leaving instances running 24/7** — EC2 templates include idle shutdown by default, but verify it's enabled. Stop ParallelCluster head nodes when not in use.
2. **Not using S3 Intelligent Tiering** — all ResearchStack S3 templates enable this by default
3. **Ignoring data transfer costs** — keep data and compute in the same region. Use VPC endpoints for S3.
4. **Not deleting failed experiments** — unused EBS volumes, old snapshots, and abandoned stacks accumulate cost silently
5. **Over-provisioning** — start small, use Compute Optimizer to right-size, scale up only when needed
6. **Not monitoring costs** — set up budget alerts using the Budget Alert template. Activate cost allocation tags.
7. **Not activating cost allocation tags** — tags exist on resources but won't appear in Cost Explorer or Budgets until [activated](#activating-cost-allocation-tags)

## Grant Budgeting Tips

1. Use [AWS Pricing Calculator](https://calculator.aws/) for initial estimates
2. Add 20-30% buffer for usage variability
3. Include F&A overhead if your institution still applies it to cloud — but note that [P.L. 119-75](#fa-and-cloud-computing) (Feb 2026) directs OMB to exclude cloud from F&A. Model accordingly.
4. Plan for [data egress costs](https://aws.amazon.com/ec2/pricing/on-demand/#Data_Transfer) if sharing data outside AWS
5. Consider [Savings Plans](https://aws.amazon.com/savingsplans/) for multi-year grants (up to 72% savings)
6. Document cost optimization strategies in your proposal — reviewers appreciate cost awareness
