# ARC Toolkit Templates

This directory contains CloudFormation templates optimized for research workloads.

## Template Categories

### Compute (`compute/`)
Templates for computational resources:
- **EC2 instances**: Various instance types for different workload patterns
- **Batch**: Managed batch computing for parallel jobs
- **ParallelCluster**: Full HPC clusters with Slurm

### Storage (`storage/`)
Templates for data storage:
- **S3**: Object storage with versioning and intelligent tiering
- **EFS**: Network file systems for shared access
- **FSx**: High-performance file systems

### Machine Learning (`ml/`)
Templates for ML/AI workloads:
- **SageMaker Studio**: Managed Jupyter environment
- **SageMaker Notebooks**: Individual notebook instances
- **Bedrock**: Foundation model access

### Data (`data/`)
Templates for data processing:
- **RDS**: Managed relational databases
- **Athena**: Serverless SQL queries
- **Glue**: ETL and data cataloging

## Template Standards

All templates follow these standards:

### Required Metadata
```yaml
Metadata:
  AWS::CloudFormation::Interface:
    # Parameter grouping for better UX
    
  ResearchLifecycle:
    Phases: ['Phase2A', 'Phase2B']  # Applicable research phases
    Description: 'When to use this template'
  
  QuickSuite:  # For future AI integration
    Keywords: ['storage', 'data', 's3']
    UseCases: ['Data collection', 'Analysis']
```

### Required Parameters
```yaml
Parameters:
  ProjectName:
    Type: String
    Description: 'Research project name (for cost tracking)'
    
  CostCenter:
    Type: String
    Description: 'Department or grant number'
    
  Owner:
    Type: String
    Description: 'PI or researcher email'
```

### Required Tags
```yaml
Tags:
  - Key: Project
    Value: !Ref ProjectName
  - Key: CostCenter
    Value: !Ref CostCenter
  - Key: Owner
    Value: !Ref Owner
  - Key: ManagedBy
    Value: ARC-Toolkit
  - Key: Environment
    Value: Research
```

### Security Defaults
- Encryption enabled by default
- Public access blocked by default
- Least privilege IAM policies
- VPC isolation where applicable

## Using Templates

### Via AWS Console
1. Navigate to CloudFormation → Create Stack
2. Upload template YAML file
3. Fill in parameters
4. Review and create

### Via AWS CLI
```bash
aws cloudformation create-stack \
  --stack-name my-stack \
  --template-body file://template.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_IAM
```

### Via Service Catalog (Phase 2)
Documentation coming soon.

## Template Structure

Each template directory contains:
- `template.yaml` - The CloudFormation template
- `README.md` - Usage guide and documentation
- `parameters.example.json` - Example parameter file
- `product.yaml` - Service Catalog configuration (Phase 2)

## Contributing Templates

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on:
- Template design standards
- Testing requirements
- Documentation requirements
- Submission process
