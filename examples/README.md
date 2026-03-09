# ARC Toolkit Examples

Example deployments and use cases.

## Available Examples

### Standalone Deployments
- **single-researcher/**: Individual researcher setup (S3 + SageMaker)
- **research-team/**: Team setup (S3 + EFS + SageMaker + ParallelCluster)
- **data-pipeline/**: Data processing pipeline (Coming in Phase 4)

### Service Catalog Deployments (Phase 2)
- **multi-account-setup/**: Service Catalog across multiple accounts
- **portfolio-configuration/**: Example portfolio configurations

## Example: Single Researcher Setup

A typical setup for an individual researcher:

```bash
# 1. Create S3 bucket for data
aws cloudformation create-stack \
  --stack-name researcher-data-bucket \
  --template-body file://templates/storage/s3-research-bucket/template.yaml \
  --parameters \
    ParameterKey=ProjectName,ParameterValue=my-research \
    ParameterKey=CostCenter,ParameterValue=grant-12345 \
    ParameterKey=Owner,ParameterValue=researcher@university.edu

# 2. Create SageMaker Studio for ML work
aws cloudformation create-stack \
  --stack-name researcher-sagemaker \
  --template-body file://templates/ml/sagemaker-studio/template.yaml \
  --parameters \
    ParameterKey=DomainName,ParameterValue=my-research \
    ParameterKey=VpcId,ParameterValue=vpc-xxxxx \
    ParameterKey=SubnetIds,ParameterValue=subnet-xxxxx\\,subnet-yyyyy \
  --capabilities CAPABILITY_IAM
```

## Example: Research Team Setup

A setup for a collaborative research team:

```bash
# 1. Create shared S3 bucket
aws cloudformation create-stack \
  --stack-name team-data-bucket \
  --template-body file://templates/storage/s3-research-bucket/template.yaml \
  --parameters file://examples/research-team/s3-parameters.json

# 2. Create shared EFS for home directories
aws cloudformation create-stack \
  --stack-name team-shared-storage \
  --template-body file://templates/storage/efs-shared-storage/template.yaml \
  --parameters file://examples/research-team/efs-parameters.json

# 3. Create SageMaker Studio with EFS integration
aws cloudformation create-stack \
  --stack-name team-sagemaker \
  --template-body file://templates/ml/sagemaker-studio/template.yaml \
  --parameters file://examples/research-team/sagemaker-parameters.json \
  --capabilities CAPABILITY_IAM

# 4. Create ParallelCluster for HPC workloads
aws cloudformation create-stack \
  --stack-name team-hpc-cluster \
  --template-body file://templates/compute/parallelcluster/template.yaml \
  --parameters file://examples/research-team/parallelcluster-parameters.json \
  --capabilities CAPABILITY_IAM
```

## Parameter Files

Example parameter files are provided in each example directory:
- `s3-parameters.json`
- `efs-parameters.json`
- `sagemaker-parameters.json`
- `parallelcluster-parameters.json`

## Cost Estimates

See individual example directories for cost estimates based on typical usage patterns.

## Coming Soon

- Data pipeline examples
- Multi-region deployments
- Compliance-focused setups (HIPAA, FedRAMP)
