# Parameter Files

One config file per template. Copy the one you need, replace `REPLACE_ME` values, and deploy:

```bash
cp params/compute-ec2.json params/my-project.json
# Edit my-project.json with your values
./deploy.sh --config params/my-project.json
```

Preview without deploying:

```bash
./deploy.sh --config params/my-project.json --dry-run
```

For interactive deployment with dropdowns, use the [CloudFormation console](https://console.aws.amazon.com/cloudformation/home#/stacks/create) instead.

## Finding Your AWS Resource IDs

Most templates need a VPC and subnet. Use these commands to find them (add `--profile your-profile` if using named profiles):

```bash
# List VPCs
aws ec2 describe-vpcs \
  --query 'Vpcs[].{Id:VpcId,CIDR:CidrBlock,Name:Tags[?Key==`Name`].Value|[0]}' \
  --output table

# List subnets in a VPC (replace vpc-xxx)
aws ec2 describe-subnets \
  --filters Name=vpc-id,Values=vpc-xxx \
  --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,CIDR:CidrBlock,Public:MapPublicIpOnLaunch,Name:Tags[?Key==`Name`].Value|[0]}' \
  --output table

# List SSH key pairs
aws ec2 describe-key-pairs --query 'KeyPairs[].KeyName' --output table

# List EFS filesystems
aws efs describe-file-systems \
  --query 'FileSystems[].{Id:FileSystemId,Name:Name,State:LifeCycleState}' \
  --output table

# List S3 buckets
aws s3 ls

# Get outputs from a deployed stack (e.g., VPC/subnet IDs from a research-vpc stack)
aws cloudformation describe-stacks \
  --stack-name research-vpc \
  --query 'Stacks[0].Outputs' --output table
```

## Available Configs

| File | What it deploys |
|------|----------------|
| `network-vpc.json` | Research VPC — deploy first, provides VPC/subnet IDs for everything else |
| `object-store-s3.json` | Encrypted S3 bucket with versioning for research data |
| `shared-filesystem-efs.json` | Network filesystem shared across multiple instances |
| `mounted-storage-s3files.json` | Mount S3 as a POSIX filesystem (~13x cheaper than EFS) |
| `parallel-filesystem-fsx.json` | High-throughput Lustre filesystem for compute-intensive I/O |
| `compute-ec2.json` | EC2 instance — change `template` key for family: `ec2-gp` (balanced), `ec2-cpu` (compute), `ec2-mem` (memory), `ec2-gpu` (GPU) |
| `compute-spot-ec2.json` | Cost-optimized Spot across multiple instance types (up to 70% savings) |
| `hpc-cluster-parallelcluster.json` | Slurm HPC cluster with DCV desktop and auto-scaling |
| `jupyter-notebook-sagemaker.json` | Managed Jupyter environment with GPU support |
| `budget-alert.json` | Monthly spend tracking with email alerts |

## Creating Your Own

Copy any file above and edit, or start from scratch:

```json
{
  "_description": "What this config deploys",
  "template": "ec2-gp",
  "stack_name": "my-stack-name",
  "parameters": {
    "ProjectName": "my-project",
    "CostCenter": "grant-12345",
    "VpcId": "vpc-abc123",
    "SubnetId": "subnet-def456"
  }
}
```

The `_description` field is ignored by the script — it's just for humans reading the file. For the full list of parameters each template accepts, see the [Templates README](../templates/README.md) or deploy via the CloudFormation console to see all parameters with descriptions.

### Template Keys

Use these in the `template` field:

| Key | Template |
|-----|----------|
| `vpc` | Research VPC |
| `s3` | S3 Research Bucket |
| `efs` | Shared File Storage (EFS) |
| `s3files` | S3 Files (Filesystem on S3) |
| `fsx` | FSx for Lustre |
| `ec2-gp` | EC2 General Purpose (M-series) |
| `ec2-cpu` | EC2 Compute Optimized (C-series) |
| `ec2-mem` | EC2 Memory Optimized (R-series) |
| `ec2-gpu` | EC2 GPU (G-series) |
| `ec2-spot` | EC2 Spot Fleet |
| `pcluster` | ParallelCluster (Slurm HPC) |
| `sagemaker` | SageMaker Studio |
| `budget` | Budget Alert |
