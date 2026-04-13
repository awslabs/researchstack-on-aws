# Research Lifecycle Guide

Map your research phase to the right AWS templates and cost strategies. This guide helps researchers, PIs, and IT admins understand what infrastructure is needed at each stage of a research project — from grant planning through long-term archival.

For cost optimization strategies at each phase, see the [Cost Optimization Guide](cost-optimization-guide.md). For template details and parameters, see the [Templates README](../templates/README.md).

## The Research Lifecycle

Research projects follow a predictable pattern of infrastructure needs. Early phases are lightweight (planning, small-scale exploration). Middle phases are compute-intensive (production runs, large-scale analysis). Late phases shift to storage-focused (archival, data sharing). Understanding where you are in this lifecycle helps you choose the right resources and avoid overspending.

```
Phase 1: Planning ──→ Phase 2A: Data Collection ──→ Phase 2B: Exploration ──→ Phase 2C: Production ──→ Phase 3: Archival
  (minimal compute)     (storage-heavy)              (iterative, bursty)      (sustained, intensive)    (storage-only)
```

## Phase 1: Planning and Grant Preparation

**Duration**: Weeks to months
**What's happening**: Grant writing, cost estimation, compliance planning, team formation

### Infrastructure Needs
Minimal — this phase is about planning, not computing. The main infrastructure activity is estimating costs for the grant budget.

### Recommended Templates
None needed yet. Use these tools for planning:
- [AWS Pricing Calculator](https://calculator.aws/) — estimate costs for the compute and storage you'll need
- [Cost Optimization Guide](cost-optimization-guide.md) — strategies for budgeting, including F&A considerations and Savings Plans

### Grant Budgeting Tips
- Budget AWS for the phases where it provides the most value — typically burst compute (Phase 2C) and long-term archival (Phase 3)
- Be specific in budget justifications: "200 GPU hours for model training at $3/hour" is stronger than "cloud computing costs"
- Include a 20-30% buffer for usage variability
- Check your institution's F&A treatment of cloud costs — see [F&A and Cloud Computing](cost-optimization-guide.md#fa-and-cloud-computing)
- If your project involves multi-institution collaboration, AWS is often the simplest shared infrastructure — call this out in the budget narrative

## Phase 2A: Data Collection and Ingress

**Duration**: Months (often ongoing throughout the project)
**What's happening**: Generating data from instruments, acquiring external datasets, initial quality control

### Infrastructure Needs
- **Storage**: Primary need — data volumes grow quickly (GBs to TBs)
- **Compute**: Moderate — data validation, format conversion, initial processing pipelines
- **Networking**: High-bandwidth data transfer if moving large datasets

### Recommended Templates

| Need | Template | Why |
|------|----------|-----|
| Store research data | [s3-research-bucket.yaml](../templates/storage/s3-research-bucket.yaml) | Versioned, encrypted, automatic cost optimization via [Intelligent Tiering](https://aws.amazon.com/s3/storage-classes/intelligent-tiering/) |
| Process incoming data | [ec2-general-purpose.yaml](../templates/compute/ec2-general-purpose.yaml) | Balanced CPU/memory for data processing scripts |
| Shared network storage | [efs-shared-storage.yaml](../templates/storage/efs-shared-storage.yaml) | When multiple instances need to read/write the same files simultaneously |
| Set up networking | [research-vpc.yaml](../templates/networking/research-vpc.yaml) | Required before deploying EC2 or EFS — creates the network your resources run in |

### Where Your Data Lives Matters

A key principle: **compute where your data lives**. Moving large datasets between locations costs time and money.

- If your data is generated on-campus (instruments, sequencers), it may make sense to process it locally first, then upload results to S3
- If your data is already in AWS (public datasets like [Registry of Open Data on AWS](https://registry.opendata.aws/), or shared by collaborators via S3), run your compute in AWS to avoid [data transfer costs](https://aws.amazon.com/ec2/pricing/on-demand/#Data_Transfer)
- For multi-institution projects where each site generates data, a shared S3 bucket is often the simplest central repository

### Cost Tips
- S3 Intelligent Tiering handles cost optimization automatically — no manual tier management needed
- Delete intermediate processing outputs once final results are validated
- Use the Budget Alert template to track spending from the start

## Phase 2B: Exploration and Method Development

**Duration**: Weeks to months
**What's happening**: Algorithm testing, parameter tuning, pilot analyses, workflow development, lots of trial and error

### Infrastructure Needs
- **Compute**: Variable and bursty — some days you need a lot, other days nothing
- **Storage**: Working datasets (subsets of full data)
- **Flexibility**: Need to try different approaches quickly — iteration speed matters more than raw throughput

### Recommended Templates

| Need | Template | Why |
|------|----------|-----|
| General analysis | [ec2-general-purpose.yaml](../templates/compute/ec2-general-purpose.yaml) | Good starting point for most workloads |
| ML development | [sagemaker-studio.yaml](../templates/ml/sagemaker-studio.yaml) | Managed Jupyter environment with GPU support — no infrastructure to manage |
| GPU experimentation | [ec2-accelerated-gpu.yaml](../templates/compute/ec2-accelerated-gpu.yaml) | When you need GPUs for training or inference outside SageMaker |
| Shared datasets | [efs-shared-storage.yaml](../templates/storage/efs-shared-storage.yaml) | When team members need access to the same working data |
| Track spending | [budget-alert.yaml](../templates/governance/budget-alert.yaml) | Set a budget early — exploration costs can creep up |

### Why Iteration Speed Matters

This phase is where cloud provides the most value over traditional HPC queues. On a shared cluster, the cycle is: submit job → wait in queue → job runs → check results → fix → resubmit. Each cycle can take hours due to queue wait times.

With EC2, the cycle is: run → check → fix → rerun. No queue. If you need to test 20 parameter combinations, you can launch 20 instances in parallel and have results in minutes instead of days.

### Cost Tips
- **Start small**: Use a smaller instance type (e.g., `m7i.xlarge`) and scale up only if you're hitting CPU or memory limits
- **Idle shutdown is on by default**: EC2 templates automatically stop instances after 90 minutes of low CPU usage — this catches forgotten instances
- **Use Spot for batch experiments**: If your work can tolerate interruption (e.g., parameter sweeps where you can rerun failed jobs), [Spot Instances](https://aws.amazon.com/ec2/spot/) save up to 70%. ParallelCluster supports Spot natively.
- **Delete what you don't need**: Failed experiments, old EBS snapshots, and test instances accumulate cost if left running

## Phase 2C: Production-Scale Computation

**Duration**: Weeks to months
**What's happening**: Large-scale simulations, genome-wide analyses, ML model training at scale, production pipeline execution

This phase has the **highest compute costs** of the entire lifecycle. The methods are established (from Phase 2B), and now you're running them at full scale on complete datasets.

### Infrastructure Needs
- **Compute**: High volume — sustained runs or massive bursts
- **Storage**: Full datasets (TBs)
- **Specialized hardware**: GPUs for ML training, high-memory instances for genomics, fast networking for tightly-coupled simulations
- **Timeline**: Often deadline-driven (publication, grant milestone)

### Recommended Templates

| Need | Template | Why |
|------|----------|-----|
| HPC cluster (Slurm) | [parallelcluster-hpc.yaml](../templates/compute/parallelcluster-hpc.yaml) | Auto-scaling compute queue, shared storage, optional remote desktop. See the [ParallelCluster Guide](parallelcluster-guide.md). |
| CPU-intensive batch | [ec2-compute-optimized.yaml](../templates/compute/ec2-compute-optimized.yaml) | C-series instances for simulations, modeling, batch processing |
| Memory-intensive | [ec2-memory-optimized.yaml](../templates/compute/ec2-memory-optimized.yaml) | R-series instances for genomics, large datasets, in-memory analysis |
| GPU training at scale | [ec2-accelerated-gpu.yaml](../templates/compute/ec2-accelerated-gpu.yaml) | G-series GPUs for ML training and inference |
| High-throughput storage | [fsx-lustre.yaml](../templates/storage/fsx-lustre.yaml) | Parallel filesystem for I/O-intensive workloads — can link directly to S3 |
| Budget enforcement | [budget-alert.yaml](../templates/governance/budget-alert.yaml) | Critical at this phase — production runs are expensive |

### Cost Tips
- **ParallelCluster auto-scaling**: Compute nodes launch on job submission and terminate when idle — you only pay for active computation. The head node runs 24/7, so stop it when the cluster isn't in use.
- **Spot Instances**: For fault-tolerant workloads (batch jobs, training with checkpointing), set `ComputePricingModel` to `SPOT` in ParallelCluster for up to 70% savings. Slurm automatically requeues interrupted jobs.
- **Savings Plans**: If you know you'll run sustained compute for months, a [Compute Savings Plan](https://aws.amazon.com/savingsplans/compute-pricing/) can save up to 72%. The breakeven is typically 7-9 months on a 1-year plan.
- **Budget alerts are critical**: Set up the Budget Alert template before starting production runs. A misconfigured pipeline can burn through a budget quickly.
- **Per-instance budgets**: EC2 templates support an optional `EnableInstanceBudget` parameter that automatically stops the instance if its project spend exceeds a configured threshold.

## Phase 3: Archival, Publication, and Data Sharing

**Duration**: Weeks (publication) to years (archival)
**What's happening**: Manuscript preparation, data sharing per funder requirements, long-term storage

### Infrastructure Needs
- **Compute**: Minimal — mostly figure generation and final analyses
- **Storage**: Long-term, cost-effective, durable
- **Access control**: Controlled access for sensitive datasets (if sharing)
- **Compliance**: Meeting funder data sharing requirements (e.g., [NIH Data Management and Sharing Policy](https://sharing.nih.gov/data-management-and-sharing-policy))

### Recommended Templates

| Need | Template | Why |
|------|----------|-----|
| Long-term data storage | [s3-research-bucket.yaml](../templates/storage/s3-research-bucket.yaml) | Intelligent Tiering automatically moves data to cheaper tiers. For deep archival, data moves to archive tiers at ~$0.001/GB/month. |
| Final analyses / figures | [ec2-general-purpose.yaml](../templates/compute/ec2-general-purpose.yaml) | If needed — most manuscript work happens on laptops |

### What to Do at This Phase

1. **Delete compute resources**: Terminate EC2 instances, delete ParallelCluster stacks, shut down SageMaker domains. Compute is the biggest cost and you don't need it anymore.
2. **Keep your data in S3**: Intelligent Tiering handles cost optimization automatically. Data you haven't accessed in 90+ days moves to archive tiers at a fraction of the cost.
3. **Share data per funder requirements**: If your funder requires data sharing (most NIH grants do), S3 with [IAM policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html) provides fine-grained access control. Many [data repositories](https://www.nlm.nih.gov/NIHbmic/nih_data_sharing_repositories.html) use AWS as their backend.
4. **Document your infrastructure**: If someone needs to reproduce your analysis, having the CloudFormation template parameters documented makes it straightforward to recreate the environment.

### Cost Tips
- [S3 Glacier Deep Archive](https://aws.amazon.com/s3/storage-classes/glacier/) is the cheapest storage option (~$0.001/GB/month). A 10TB dataset costs ~$10/month to archive.
- Delete everything you don't need to keep — intermediate outputs, temporary EBS volumes, old snapshots
- If you're done with the project entirely, delete the VPC stack too (NAT gateways cost ~$32/month even when idle)

## Quick Reference: Template by Need

| Need | Template | Phase |
|------|----------|-------|
| Object storage | s3-research-bucket.yaml | 2A, 3 |
| Shared file system | efs-shared-storage.yaml | 2A, 2B, 2C |
| High-throughput storage | fsx-lustre.yaml | 2C |
| General compute | ec2-general-purpose.yaml | 2A, 2B |
| CPU-intensive compute | ec2-compute-optimized.yaml | 2C |
| Memory-intensive compute | ec2-memory-optimized.yaml | 2C |
| GPU compute | ec2-accelerated-gpu.yaml | 2B, 2C |
| HPC cluster (Slurm) | parallelcluster-hpc.yaml | 2C |
| ML development | sagemaker-studio.yaml | 2B |
| Networking (VPC) | research-vpc.yaml | 2A (deploy first) |
| Budget tracking | budget-alert.yaml | All phases |

## Collaboration Considerations

The complexity of your collaboration affects infrastructure choices:

**Solo PI / Single Lab**: Templates deployed in one account are usually sufficient. Shared storage (EFS or S3) handles team data access within the same VPC.

**Multi-Lab (Same Institution)**: Same approach, but consider a shared VPC and S3 bucket across labs. Service Catalog governance helps standardize deployments. Cost center tags enable per-lab chargeback.

**Multi-Institution Consortium**: AWS becomes the natural collaboration hub. A shared S3 bucket with [IAM policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html) gives each institution controlled access without VPN complexity. Each institution can run compute in their own account against the shared data. This is where [Service Catalog](service-catalog-guide.md) with OU sharing provides the most governance value.

**International Collaboration**: AWS [regions](https://aws.amazon.com/about-aws/global-infrastructure/regions_az/) solve data sovereignty requirements — EU data stays in an EU region, US data stays in a US region. No cross-border data transfer needed.
