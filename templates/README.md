# ResearchStack on AWS Templates

CloudFormation templates optimized for research workloads. Each template can be deployed standalone via the AWS Console or CLI, or governed via [Service Catalog](../docs/service-catalog-guide.md).

## Getting Started

Most templates require a VPC (a virtual network in AWS) and a subnet (a segment within that network). If you don't have one, deploy `research-vpc.yaml` first — it creates a ready-to-use network with public and private subnets, a NAT gateway for internet access, and an S3 endpoint. Then deploy compute, storage, or ML templates into that VPC using the VPC ID and subnet IDs from the stack outputs.

If your institution already provides a VPC (common with [Landing Zone Accelerator](https://aws.amazon.com/solutions/implementations/landing-zone-accelerator-on-aws/) or [Control Tower](https://aws.amazon.com/controltower/)), use those VPC and subnet IDs directly — no need to deploy the VPC template.

## Available Templates

### Networking (`networking/`)
- **research-vpc.yaml** — Reusable VPC with public/private subnets, NAT gateway, S3 gateway endpoint, and configurable AZs. Note: the NAT gateway has a base cost (~$32/mo) plus data processing charges — delete the stack when not in use to avoid idle costs.

### Storage (`storage/`)
- **s3-research-bucket.yaml** — Secure S3 bucket with versioning, encryption, intelligent tiering, and HTTPS-only policy
- **efs-shared-storage.yaml** — Network file system for shared access across multiple instances. EC2 instances must have the EFS security group (from stack outputs) attached to mount the filesystem.
- **fsx-lustre.yaml** — High-throughput parallel filesystem for compute-intensive workloads. Supports S3 data repository associations for transparent access to S3 data.

### Compute (`compute/`)
- **ec2-general-purpose.yaml** — M-series instances for balanced workloads (data processing, web apps, dev environments)
- **ec2-compute-optimized.yaml** — C-series instances for compute-intensive tasks (simulations, batch processing, modeling)
- **ec2-memory-optimized.yaml** — R-series instances for memory-intensive workloads (genomics, large datasets, in-memory DBs)
- **ec2-accelerated-gpu.yaml** — GPU (G/P-series) and Trainium/Inferentia for ML training and inference
- **parallelcluster-hpc.yaml** — Full HPC cluster with Slurm scheduler, shared storage, and optional DCV remote desktop. See the [ParallelCluster Guide](../docs/parallelcluster-guide.md) for deployment, job submission, and post-deploy customization (adding queues, multi-user, login nodes).

All EC2 templates require a VPC and subnet — deploy the Research VPC template first if you don't have one. Instance types are constrained by family (e.g., M-series for general purpose) but not pinned to specific generations, so new instance types work automatically as AWS releases them.

### Machine Learning (`ml/`)
- **sagemaker-studio.yaml** — Managed Jupyter environment with GPU support. Configured for [IAM Identity Center](https://aws.amazon.com/iam/identity-center/) (SSO) authentication — requires IDC to be enabled in your account. After deployment, assign users or IDC groups to the domain in the [SageMaker console](https://console.aws.amazon.com/sagemaker/) under **Domains** → your domain → **User profiles**.

### Governance (`governance/`)
- **budget-alert.yaml** — Monthly budget tracking by CostCenter tag with email alerts at 50%, 80%, and 100% thresholds. Optionally scoped to a specific project. Requires cost allocation tags to be activated first — see the [Cost Optimization Guide](../docs/cost-optimization-guide.md).

## Template Standards

All templates follow these conventions:

- **Required parameters**: ProjectName, CostCenter (Owner is optional)
- **Required tags**: Project, CostCenter, ManagedBy (ResearchStack), Environment (Research)
- **Security defaults**: Encryption enabled, public access blocked, least privilege where applicable
- **Naming**: Resources include account ID and region for uniqueness

## Choosing an Instance Type

Not sure which instance size to pick? Each EC2 template constrains you to the right family (M for general purpose, C for compute, etc.) but leaves the size up to you. These resources can help:

- [AWS EC2 Instance Types](https://aws.amazon.com/ec2/instance-types/) — official specs and family descriptions
- [Vantage Instance Comparison](https://instances.vantage.sh/?id=421e512ec7fc071920ffc00ca2bc7141ef1c98aa) — community tool for comparing specs, pricing, and availability side-by-side (filter by family, sort by price)

When in doubt, start small (e.g., `m7i.xlarge`) and scale up. You can always stop the instance, change the type, and restart.

For Graviton (arm64) instances (e.g., `m7g`, `c7g`, `r7g`), select the arm64 AMI variant from the dropdown — typically ~20% better price-performance than x86.

### Available Operating Systems

Each EC2 template offers these AMIs via SSM parameter lookup (always resolves to the latest version):

| Dropdown value | OS | Architecture |
|---|---|---|
| `al2023-ami-kernel-default-x86_64` | Amazon Linux 2023 | x86_64 (Intel/AMD) |
| `al2023-ami-kernel-default-arm64` | Amazon Linux 2023 | arm64 (Graviton) |
| `ubuntu/server/noble/.../amd64` | Ubuntu 24.04 LTS | x86_64 (Intel/AMD) |
| `ubuntu/server/noble/.../arm64` | Ubuntu 24.04 LTS | arm64 (Graviton) |

Amazon Linux 2023 is the default and recommended for most workloads — EFS auto-mounts with TLS encryption and SSM works out of the box. Ubuntu 24.04 is supported for teams that prefer it, but EFS must be mounted manually post-boot because `amazon-efs-utils` now requires a Rust toolchain to build on Ubuntu. See the [efs-utils GitHub repo](https://github.com/aws/efs-utils) for manual install instructions.

## Connecting to Instances

All EC2 templates use [SSM Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html) for access — no SSH keys, no inbound ports, no public IP required. Connect via:

```bash
aws ssm start-session --target i-0123456789abcdef0 [--profile your-profile-name]
```

The instance ID and connect command are in the stack outputs after deployment. Requires the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) for the AWS CLI.

## Deploying

### Via AWS Console
1. Go to CloudFormation → Create Stack
2. Upload the template YAML
3. Fill in parameters (Project, CostCenter, etc.)
4. Create stack

### Via AWS CLI
```bash
aws cloudformation create-stack \
  --stack-name my-research-bucket \
  --template-body file://storage/s3-research-bucket.yaml \
  --parameters \
    ParameterKey=ProjectName,ParameterValue=my-project \
    ParameterKey=CostCenter,ParameterValue=dept-123
```

### Via Service Catalog
See the [Service Catalog Deployment Guide](../docs/service-catalog-guide.md) for multi-account governed deployment.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for template design guidelines and submission process.
