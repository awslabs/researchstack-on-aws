# AWS Research Cloud (ARC) Toolkit

A template-first, maintainable solution for research institutions and research teams deploying AWS resources, including EC2 instances, S3 buckets, SageMaker Domains, and more. The ARC Toolkit provides CloudFormation templates optimized for research workloads, with optional Service Catalog governance and AI-powered deployment assistance.

## Why ARC?

Research institutions have three personas that all need something different from AWS:

- **Researchers** want to jump into their work at whatever phase of the research lifecycle they're in — not learn networking, security groups, and IAM. ARC gives them pre-built templates that handle the infrastructure so they can focus on research.
- **IT admins** want researchers to self-serve compute and storage, but using best practices and in a standardized way so that troubleshooting is repeatable. ARC templates enforce security defaults, consistent architecture, and known-good configurations across the institution.
- **FinOps teams** need cost visibility across grants and an easy path to chargeback. Every ARC-deployed resource is automatically tagged with project, cost center, and owner — ready for Cost and Usage Reports without manual tagging.

## Architecture

<!-- TODO: Add high-level architecture diagram (draw.io) -->
<!-- Diagram should show:
  - Two deployment paths side by side:
    1. Standalone: User → CloudFormation → AWS Resources (with tags)
    2. Service Catalog: Hub Account → SC Portfolio → OU Sharing → Spoke Accounts → AWS Resources (with tags)
  - Template categories feeding into both paths (compute, storage, ml, networking)
  - Cost tracking flow: Tags → Cost and Usage Reports → Grant Chargeback
  - Future: Quick Suite AI layer sitting above both paths
  - OU evolution note: Institutions typically start with a single "Research" OU, then split over time
    into purpose-specific OUs (e.g., Research-Sandbox, Research-HIPAA, Research-Production).
    Show this as a callout or dashed-line expansion on the SC path.
  - TODO (future arch section): Discuss OU scaling best practices, link to AWS Organizing Your Environment
    whitepaper, and call out how LZA / Secure Research Environment accelerate compliance-heavy OU structures.
-->

## Overview

The ARC Toolkit helps research institutions:
- **Deploy quickly**: Pre-built CloudFormation templates for common research workloads
- **Track costs**: Built-in tagging for grant chargeback
- **Scale governance**: Optional Service Catalog for multi-account template governance and deployment
- **Accelerate adoption**: AI-powered template selection and deployment (coming soon)

## Repository Structure

```
aws-research-cloud/
├── templates/                # CloudFormation templates
│   ├── compute/             # EC2, ParallelCluster
│   ├── storage/             # S3, EFS
│   ├── ml/                  # SageMaker
│   ├── networking/          # VPC
│   └── data/                # (future: RDS, Athena)
├── service-catalog/          # CDK code for Service Catalog deployment
│   ├── app.py               # CDK entrypoint
│   ├── framework_config.yaml # Deployment settings (account, region, org)
│   ├── portfolios/          # Portfolio TOML configs with inline products
│   ├── stacks/              # CDK stacks (assets, portfolio)
│   ├── sc_constructs/       # CDK constructs (launch roles, StackSets, sharing)
│   ├── core/                # Config loaders (framework YAML, portfolio TOML)
│   └── utils/               # Naming, tagging, global config
├── docs/                    # Documentation
│   ├── research-lifecycle-guide.md
│   └── cost-optimization-guide.md
├── ADRs/                    # Architecture Decision Records
├── CONTRIBUTING.md
└── README.md
```

## Quick Start

### Option 1: Deploy Templates Directly (Standalone)

For IT admins or lab leads deploying resources in a single account or small team.

1. **Choose a template** from the `templates/` directory
2. **Deploy via AWS Console**:
   - Go to CloudFormation → Create Stack
   - Upload the template YAML file
   - Fill in parameters (Project, CostCenter, Owner)
   - Create stack

3. **Or deploy via AWS CLI**:
   ```bash
   aws cloudformation create-stack \
     --stack-name my-research-bucket \
     --template-body file://templates/storage/s3-research-bucket.yaml \
     --parameters \
       ParameterKey=ProjectName,ParameterValue=my-project \
       ParameterKey=CostCenter,ParameterValue=grant-12345 \
       ParameterKey=Owner,ParameterValue=researcher@university.edu
   ```

### Option 2: Deploy via Service Catalog (Governance for Multi-Account)

For IT admins or cloud teams setting up governed self-service across multiple accounts. Once deployed, researchers consume templates through the Service Catalog console.

Service Catalog wraps the same templates with portfolio-based access control, OU sharing, and per-product launch roles. It uses CDK because StackSets, launch role lifecycle, and portfolio dependencies require state management that raw CloudFormation doesn't handle well.

Prerequisites: Python 3.11+, AWS CLI, CDK CLI (`npm install -g aws-cdk`), AWS Organizations with delegated admin for Service Catalog and CloudFormation StackSets.

```bash
cd service-catalog
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Edit framework_config.yaml with your account, region, org ID
# Edit portfolios/research-computing.toml with your OU IDs

cdk bootstrap aws://ACCOUNT_ID/REGION
cdk deploy --all
```

After deployment, grant portfolio access in the SC console. See the [Service Catalog Deployment Guide](docs/service-catalog-guide.md) for full prerequisites, configuration details, and post-deployment steps.

## Common Deployment Patterns

### Pattern 1: Shared VPC + Multiple Resources

Deploy a VPC once, then reuse it for multiple resources:

```bash
# 1. Deploy VPC once
aws cloudformation create-stack \
  --stack-name research-vpc \
  --template-body file://templates/networking/research-vpc.yaml \
  --parameters \
    ParameterKey=ProjectName,ParameterValue=research-network \
    ParameterKey=CostCenter,ParameterValue=dept-123 \
    ParameterKey=Owner,ParameterValue=admin@university.edu

# 2. Get VPC ID from outputs
VPC_ID=$(aws cloudformation describe-stacks --stack-name research-vpc \
  --query 'Stacks[0].Outputs[?OutputKey==`VpcId`].OutputValue' --output text)

SUBNET_ID=$(aws cloudformation describe-stacks --stack-name research-vpc \
  --query 'Stacks[0].Outputs[?OutputKey==`PublicSubnetId`].OutputValue' --output text)

# 3. Deploy resources using that VPC
aws cloudformation create-stack \
  --stack-name my-ec2 \
  --template-body file://templates/compute/ec2-general-purpose.yaml \
  --parameters \
    ParameterKey=VpcId,ParameterValue=$VPC_ID \
    ParameterKey=SubnetId,ParameterValue=$SUBNET_ID \
    ParameterKey=ProjectName,ParameterValue=my-project \
    ParameterKey=CostCenter,ParameterValue=grant-12345 \
    ParameterKey=Owner,ParameterValue=researcher@university.edu
```

### Pattern 2: Standalone Resources (VPC created automatically)

EC2 templates create a VPC automatically if you don't provide one:

```bash
# Just deploy - VPC will be created
aws cloudformation create-stack \
  --stack-name my-ec2 \
  --template-body file://templates/compute/ec2-general-purpose.yaml \
  --parameters \
    ParameterKey=ProjectName,ParameterValue=my-project \
    ParameterKey=CostCenter,ParameterValue=grant-12345 \
    ParameterKey=Owner,ParameterValue=researcher@university.edu \
    ParameterKey=InstanceType,ParameterValue=m7i.xlarge
```

## Templates

### Networking
- **research-vpc.yaml**: Reusable VPC with public/private subnets, NAT gateway, and VPC endpoints

### Storage
- **s3-research-bucket.yaml**: Secure S3 bucket with versioning and intelligent tiering
- **efs-shared-storage.yaml**: Network file system for shared access

### Compute
- **ec2-general-purpose.yaml**: M-series instances for balanced workloads
- **ec2-compute-optimized.yaml**: C-series instances for compute-intensive tasks
- **ec2-memory-optimized.yaml**: R-series instances for memory-intensive workloads
- **ec2-accelerated-gpu.yaml**: GPU (G/P-series) and Trainium/Inferentia for ML
- **ec2-hpc-optimized.yaml**: HPC-optimized instances for parallel workloads
- **parallelcluster-hpc.yaml**: Full HPC cluster with Slurm scheduler

### Machine Learning
- **sagemaker-studio.yaml**: Managed Jupyter environment with GPU support

## Cost Tracking

All templates include required tags for cost allocation:
- **Project**: Research project name
- **CostCenter**: Department or grant number
- **Owner**: PI or researcher email
- **ManagedBy**: Always "ARC-Toolkit"
- **Environment**: Always "Research"

Use these tags in AWS Cost Explorer for chargeback reporting. See the [Cost Optimization Guide](docs/cost-optimization-guide.md) for enabling cost allocation tags, setting up Cost and Usage Reports, and grant budgeting tips.

## Documentation

- [Service Catalog Deployment Guide](docs/service-catalog-guide.md) - Full walkthrough for multi-account governance deployment
- [Research Lifecycle Guide](docs/research-lifecycle-guide.md) - Map your research phase to appropriate templates
- [Cost Optimization Guide](docs/cost-optimization-guide.md) - Strategies to minimize AWS costs
- [Contributing Guide](CONTRIBUTING.md) - How to contribute templates

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/aws-research-cloud/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/aws-research-cloud/discussions)
- **AWS Support**: Contact your AWS account team

## Roadmap

- **Phase 1** (Complete): Repository structure + initial templates
- **Phase 2** (Current): Service Catalog integration (simplified CDK)
- **Phase 3**: Gen AI-powered deployment
- **Phase 4**: Additional templates and community expansion

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing templates and documentation.
