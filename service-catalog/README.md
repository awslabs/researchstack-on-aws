# ResearchStack on AWS — Service Catalog (CDK)

CDK project that deploys Service Catalog portfolios, products, launch roles, and OU sharing on top of the [CloudFormation templates](../templates/).

For full deployment instructions, prerequisites, and configuration details, see the [Service Catalog Deployment Guide](../docs/service-catalog-guide.md).

## Quick Reference

```
service-catalog/
├── app.py                    # CDK entrypoint
├── framework_config.yaml     # Deployment settings (account, region, org)
├── portfolios/               # Portfolio TOML configs with inline products
├── stacks/                   # CDK stacks (assets, portfolio)
├── sc_constructs/            # CDK constructs (launch roles, StackSets, sharing)
├── core/                     # Config loaders (framework YAML, portfolio TOML)
└── utils/                    # Naming, tagging, global config
```
