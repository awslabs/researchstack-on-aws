# ARC Toolkit Templates

CloudFormation templates optimized for research workloads. Each template can be deployed standalone via the AWS Console or CLI, or governed via [Service Catalog](../docs/service-catalog-guide.md).

## Available Templates

### Networking (`networking/`)
- **research-vpc.yaml** — Reusable VPC with public/private subnets, NAT gateway, and VPC endpoints

### Storage (`storage/`)
- **s3-research-bucket.yaml** — Secure S3 bucket with versioning, encryption, intelligent tiering, and HTTPS-only policy
- **efs-shared-storage.yaml** — Network file system for shared access across multiple instances

### Compute (`compute/`)
- **ec2-general-purpose.yaml** — M-series instances for balanced workloads
- **ec2-compute-optimized.yaml** — C-series instances for compute-intensive tasks
- **ec2-memory-optimized.yaml** — R-series instances for memory-intensive workloads
- **ec2-accelerated-gpu.yaml** — GPU (G/P-series) and Trainium/Inferentia for ML
- **ec2-hpc-optimized.yaml** — HPC-optimized instances for parallel workloads
- **parallelcluster-hpc.yaml** — Full HPC cluster with Slurm scheduler, shared storage, and DCV remote desktop

### Machine Learning (`ml/`)
- **sagemaker-studio.yaml** — Managed Jupyter environment with GPU support

## Template Standards

All templates follow these conventions:

- **Required parameters**: ProjectName, CostCenter (Owner is optional)
- **Required tags**: Project, CostCenter, ManagedBy (ARC-Toolkit), Environment (Research)
- **Security defaults**: Encryption enabled, public access blocked, least privilege where applicable
- **Naming**: Resources include account ID and region for uniqueness

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
