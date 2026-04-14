# ResearchStack on AWS

Production-ready CloudFormation templates for research computing — deploy EC2, S3, EFS, SageMaker, ParallelCluster, and more with built-in security, cost tracking, and governance. From a single researcher to a multi-account institution.

## Why ResearchStack?

- **Researchers**: Deploy compute and storage in minutes, not days. No networking or IAM knowledge needed — just pick a template, fill in your project name and cost center, and launch.
- **IT admins**: Give researchers self-service access to standardized, security-hardened infrastructure. Every deployment follows the same architecture, making troubleshooting repeatable.
- **FinOps teams**: Every resource is automatically tagged with project, cost center, and owner — ready for [Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) and grant chargeback without manual tagging.

## Architecture

<!-- TODO: Add high-level architecture diagram -->

ResearchStack supports two deployment paths:

- **Standalone**: deploy templates directly via the [CloudFormation](https://aws.amazon.com/cloudformation/) console or [AWS CLI](https://aws.amazon.com/cli/) into any AWS account — simplest for single accounts and small teams
- **Service Catalog**: deploy a governance layer to share templates across multiple accounts via a hub-and-spoke model with per-product deployment permissions and OU-level sharing — best for institutions managing multiple researcher accounts

Both paths use the same templates and produce the same tagged resources.

## What's Included

- **CloudFormation templates** for compute, storage, ML, networking, and cost governance
- **Service Catalog integration** for multi-account governance with launch roles and OU sharing
- **Cost tracking** via tags on every resource (Project, CostCenter, Owner)
- **Budget alerts** with optional per-instance enforcement
- **Idle shutdown** on EC2 instances (stops forgotten instances automatically)
- **Documentation** for every template, the research lifecycle, cost optimization, and HPC clusters

## Templates

| Category | Template | What it does |
|----------|----------|-------------|
| Networking | research-vpc.yaml | VPC with public/private subnets, NAT gateway, S3 endpoint |
| Storage | s3-research-bucket.yaml | Encrypted S3 bucket with versioning and intelligent tiering |
| Storage | efs-shared-storage.yaml | Shared network filesystem (NFS) across multiple instances |
| Storage | fsx-lustre.yaml | High-throughput parallel filesystem for compute-intensive I/O |
| Compute | ec2-general-purpose.yaml | M-series instances for balanced workloads |
| Compute | ec2-compute-optimized.yaml | C-series instances for simulations and batch processing |
| Compute | ec2-memory-optimized.yaml | R-series instances for genomics and large datasets |
| Compute | ec2-accelerated-gpu.yaml | GPU instances (G-series) for ML training and inference |
| Compute | parallelcluster-hpc.yaml | Slurm HPC cluster with auto-scaling and optional remote desktop |
| ML | sagemaker-studio.yaml | Managed Jupyter environment with GPU support |
| Governance | budget-alert.yaml | Monthly budget tracking by cost center with email alerts |

See the [Templates README](templates/README.md) for detailed descriptions, instance type guidance, and OS options.

Not sure which template fits your work? The [Research Lifecycle Guide](docs/research-lifecycle-guide.md) maps each phase of a research project to the right templates and cost strategies. For budgeting, Savings Plans, and F&A guidance, see the [Cost Optimization Guide](docs/cost-optimization-guide.md).

## Quick Start

### Deploy via AWS Console (simplest)

1. Open the [CloudFormation console](https://console.aws.amazon.com/cloudformation/home#/stacks/create)
2. Choose "Upload a template file" and select a template YAML from `templates/`
3. Fill in parameters — at minimum: ProjectName, CostCenter, and any resource-specific settings
4. Click through to "Create stack"

Most templates require a VPC and subnet. Deploy `research-vpc.yaml` first if you don't have one.

### Deploy via AWS CLI

Requires the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed with [credentials configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).

```bash
# Deploy a VPC first (if you don't have one)
aws cloudformation create-stack \
  --stack-name research-vpc \
  --template-body file://templates/networking/research-vpc.yaml \
  --parameters \
    ParameterKey=ProjectName,ParameterValue=my-project \
    ParameterKey=CostCenter,ParameterValue=grant-12345

# Then deploy resources into that VPC (get VPC/subnet IDs from the stack outputs)
aws cloudformation create-stack \
  --stack-name my-ec2 \
  --template-body file://templates/compute/ec2-general-purpose.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=ProjectName,ParameterValue=my-project \
    ParameterKey=CostCenter,ParameterValue=grant-12345 \
    ParameterKey=VpcId,ParameterValue=vpc-xxxxxxxx \
    ParameterKey=SubnetId,ParameterValue=subnet-xxxxxxxx
```

### Deploy via Service Catalog (multi-account governance)

For institutions managing multiple AWS accounts with governed self-service. Researchers browse a catalog and click "Launch" — no CloudFormation knowledge needed.

See the [Service Catalog Deployment Guide](docs/service-catalog-guide.md) for full setup.

## Cost Tracking and Access Control

All templates automatically tag resources for cost allocation:
- **Project**: Research project name
- **CostCenter**: Department or grant number
- **Owner**: PI or researcher email
- **ManagedBy**: ResearchStack
- **Environment**: Research

Use these tags in [AWS Cost Explorer](https://console.aws.amazon.com/cost-management/home#/cost-explorer) for per-grant chargeback. See the [Cost Optimization Guide](docs/cost-optimization-guide.md) for activating cost allocation tags, setting up budgets, and grant budgeting strategies.

For access control, the simplest and most effective approach is account-level isolation — one AWS account per lab or research group, with [IAM Identity Center](https://aws.amazon.com/iam/identity-center/) permission sets granting access. Researchers get broad permissions within their account because everything in it belongs to their project. The account boundary is the access control. For institutions using shared accounts, IDC groups can be mapped to permission sets with tag-scoped policies, though this has limitations for researchers on multiple projects. ResearchStack doesn't ship IAM policies (access control is institution-specific), but the consistent resource tagging supports both approaches.

## Repository Structure

```
researchstack/
├── templates/                # CloudFormation templates (the core product)
│   ├── compute/             # EC2, ParallelCluster
│   ├── storage/             # S3, EFS, FSx Lustre
│   ├── ml/                  # SageMaker
│   ├── networking/          # VPC
│   ├── governance/          # Budget alerts
│   └── data/                # (future: RDS, Athena)
├── service-catalog/          # CDK code for Service Catalog governance layer
├── docs/                    # Documentation
├── ADRs/                    # Architecture Decision Records
└── CONTRIBUTING.md
```

## Documentation

- [Templates README](templates/README.md) — Template details, instance types, OS options, deployment instructions
- [Research Lifecycle Guide](docs/research-lifecycle-guide.md) — Map your research phase to the right templates
- [Cost Optimization Guide](docs/cost-optimization-guide.md) — Budgeting, Savings Plans, F&A guidance, cost tracking
- [ParallelCluster Guide](docs/parallelcluster-guide.md) — Deploy, connect, run jobs, and customize HPC clusters
- [Service Catalog Deployment Guide](docs/service-catalog-guide.md) — Multi-account governance setup
- [Service Catalog Developer Guide](service-catalog/README.md) — Code architecture for contributors
- [Contributing Guide](CONTRIBUTING.md) — Template standards and submission process

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/researchstack/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/researchstack/discussions)
- **AWS Support**: Contact your AWS account team

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.
