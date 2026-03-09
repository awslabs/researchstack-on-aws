# AWS Research Cloud (ARC) Toolkit

A template-first, maintainable solution for research institutions deploying AWS resources. The ARC Toolkit provides CloudFormation templates optimized for research workloads, with optional Service Catalog governance and AI-powered deployment assistance.

## Overview

The ARC Toolkit helps research institutions:
- **Deploy quickly**: Pre-built CloudFormation templates for common research workloads
- **Track costs**: Built-in tagging for grant chargeback and F&A calculations
- **Scale governance**: Optional Service Catalog for multi-account deployments
- **Accelerate adoption**: AI-powered template selection and deployment (coming soon)

## Repository Structure

```
aws-research-cloud/
├── templates/                # CloudFormation templates (Phase 1)
│   ├── compute/             # EC2, ParallelCluster
│   ├── storage/             # S3, EFS
│   ├── ml/                  # SageMaker
│   ├── networking/          # VPC
│   └── data/                # (future: RDS, Athena)
├── service-catalog/          # CDK code for SC deployment (Phase 2)
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

Service Catalog wraps the same templates with portfolio-based access control, OU sharing, and per-product launch roles.

1. **Configure** — edit `service-catalog/framework_config.yaml` with your account, region, and org ID
2. **Define portfolios** — edit or create TOML files in `service-catalog/portfolios/` (see `research-computing.toml` for the example)
3. **Deploy**:
   ```bash
   cd service-catalog
   pip install -e .
   cdk bootstrap aws://ACCOUNT_ID/REGION
   cdk deploy --all
   ```
4. **Grant access** — in the AWS Console, share the portfolio with IAM Identity Center groups or roles

Prerequisites: AWS Organizations, delegated admin for Service Catalog and CloudFormation StackSets in the hub account.

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

Use these tags in AWS Cost Explorer for chargeback reporting.

## Documentation

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
- **Phase 3**: Quick Suite AI-powered deployment
- **Phase 4**: Additional templates and community expansion

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing templates and documentation.
