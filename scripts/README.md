# Research Cloud Toolkit on AWS Scripts

Utility scripts for template validation and deployment.

## Available Scripts

### validate-template.py
Validates CloudFormation templates against Research Cloud Toolkit on AWS standards.

**Usage:**
```bash
python scripts/validate-template.py templates/storage/s3-research-bucket/template.yaml
```

**Checks:**
- Required metadata sections (ResearchLifecycle, QuickSuite)
- Required parameters (ProjectName, CostCenter, Owner)
- Required tags on all resources
- Security defaults (encryption, public access blocking)
- Parameter validation patterns

**Coming Soon:**
- Cost estimation script
- Batch validation for all templates
- Template generator for new templates

## Requirements

```bash
pip install boto3 pyyaml cfn-lint
```

## Development

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on adding new scripts.
