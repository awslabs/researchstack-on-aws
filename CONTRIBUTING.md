# Contributing to ResearchStack on AWS

## Template Standards

All templates must follow these standards.

### Required Parameters

```yaml
Parameters:
  ProjectName:
    Type: String
    AllowedPattern: '^[a-zA-Z0-9-]+'
    MinLength: 3
    MaxLength: 40

  CostCenter:
    Type: String
    MinLength: 1

  Owner:
    Type: String
    Default: ''
    Description: 'PI or researcher email (optional)'
```

### Required Tags

All taggable resources must include:

```yaml
Tags:
  - Key: Project
    Value: !Ref ProjectName
  - Key: CostCenter
    Value: !Ref CostCenter
  - !If
    - HasOwner
    - Key: Owner
      Value: !Ref Owner
    - !Ref 'AWS::NoValue'
  - Key: ManagedBy
    Value: ResearchStack
  - Key: Environment
    Value: Research
```

### Parameter Grouping

Use `AWS::CloudFormation::Interface` metadata to group parameters logically. Always put Research Project Information (ProjectName, CostCenter, Owner) first:

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
      - Label:
          default: 'Resource Configuration'
        Parameters:
          - ...
```

### Security Defaults

- Encryption enabled by default
- Public access blocked by default
- Least privilege IAM policies
- VPC isolation where applicable

### File Naming

- Use kebab-case: `ec2-general-purpose.yaml`
- Place in appropriate category folder: `templates/compute/`, `templates/storage/`, `templates/ml/`, `templates/networking/`, `templates/governance/`
- YAML format only

## Submitting Templates

1. Fork the repository
2. Create template following standards above
3. Test template deployment
4. Add the template to `templates/README.md`
5. If adding to Service Catalog, add a `[[portfolio.products]]` entry to the appropriate portfolio TOML
6. Submit pull request

## Questions

Open an issue or discussion on GitHub.
