# Contributing to ResearchStack on AWS

## Template Standards

All templates must follow these standards:

### Required Metadata

```yaml
Metadata:
  AWS::CloudFormation::Interface:
    ParameterGroups:
      - Label:
          default: 'Research Project Information'
        Parameters:
          - ProjectName
          - CostCenter
          - Owner
  
  ResearchLifecycle:
    Phases:
      - Phase2A  # Data Collection
      - Phase2B  # Exploration
      - Phase2C  # Production
      - Phase3   # Archival
    Description: 'When to use this template'
  
  QuickSuite:
    Keywords:
      - relevant
      - keywords
    UseCases:
      - Use case 1
      - Use case 2
```

### Required Parameters

```yaml
Parameters:
  ProjectName:
    Type: String
    AllowedPattern: '^[a-zA-Z0-9-]+$'
    MinLength: 3
    MaxLength: 40
  
  CostCenter:
    Type: String
    MinLength: 1
  
  Owner:
    Type: String
    AllowedPattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
```

### Required Tags

All resources must have these tags:

```yaml
Tags:
  - Key: Project
    Value: !Ref ProjectName
  - Key: CostCenter
    Value: !Ref CostCenter
  - Key: Owner
    Value: !Ref Owner
  - Key: ManagedBy
    Value: ResearchStack
  - Key: Environment
    Value: Research
```

### Security Defaults

- Encryption enabled by default
- Public access blocked by default
- Least privilege IAM policies
- VPC isolation where applicable

### File Naming

- Use kebab-case: `ec2-general-purpose.yaml`
- Place in appropriate category folder: `templates/compute/`, `templates/storage/`, etc.
- YAML format only

## Submitting Templates

1. Fork the repository
2. Create template following standards above
3. Test template deployment
4. Submit pull request
5. Respond to review feedback

## Questions

Open an issue or discussion on GitHub.
