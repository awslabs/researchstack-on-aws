# Service Catalog Deployment Guide

This guide walks through deploying the ARC Toolkit's Service Catalog layer, which adds portfolio-based governance, OU sharing, and per-product launch roles on top of the CloudFormation templates.

## Architecture

<!-- TODO: Add Service Catalog architecture diagram (draw.io) -->
<!-- Diagram should show:
  - Hub Account (center):
    - CDK deploys: Assets S3 Bucket, SC Portfolio, Products (linked to CFN templates)
    - Per-product Launch Roles created locally in hub
  - StackSets (arrows from hub to spoke accounts):
    - Launch Role StackSets push per-product IAM roles into spoke accounts
  - Spoke Accounts (in target OUs):
    - Receive portfolio share via OU sharing
    - Launch roles exist locally (created by StackSets)
    - Users provision products → CloudFormation creates resources with tags
  - AWS Organizations context:
    - Management Account delegates SC + StackSets admin to Hub Account
    - OUs contain spoke accounts
  - Flow: CDK deploy → Assets Bucket + Portfolio + StackSets → OU Share → Spoke users see portfolio → Provision product → Launch role scopes permissions → CFN creates tagged resources
-->

## Why CDK?

Service Catalog deployment uses CDK (not raw CloudFormation or boto3) because:
- StackSets for launch roles require lifecycle management (create, update, delete across accounts)
- Portfolio → product → launch role → StackSet dependencies need ordering
- CDK handles drift detection and state tracking automatically

You don't need to know CDK to use this — just edit config files and run `cdk deploy`.

## Prerequisites

### AWS Account Setup
- AWS Organizations enabled
- A designated hub account for Service Catalog
- Hub account is **delegated administrator** for:
  - AWS Service Catalog
  - CloudFormation StackSets
- Target OUs exist in your organization

To enable delegated admin (run from the management account):
```bash
aws organizations register-delegated-administrator \
  --account-id HUB_ACCOUNT_ID \
  --service-principal servicecatalog.amazonaws.com

aws organizations enable-aws-service-access \
  --service-principal member.org.stacksets.cloudformation.amazonaws.com
```

### Local Tools
- Python 3.11+
- AWS CLI configured with hub account credentials (`aws configure`)
- CDK CLI: `npm install -g aws-cdk`

Verify:
```bash
python3 --version   # 3.11+
aws sts get-caller-identity   # should show hub account
cdk --version
```

## Configuration

### 1. Framework Config (`service-catalog/framework_config.yaml`)

Set your deployment target:
```yaml
deployment:
  hub_account: "123456789012"       # Your hub account ID
  hub_region: "us-east-1"           # Deployment region
  organization_id: "o-exampleorgid" # Your AWS Organization ID
  default_env_name: "dev"

available_ous:
  - "ou-xxxx-xxxxxxxx"  # OUs that portfolios can share to
```

### 2. Portfolio Config (`service-catalog/portfolios/*.toml`)

Each TOML file defines a portfolio with inline products. The example `research-computing.toml` includes all ARC templates. Customize it:

- Add/remove products by editing `[[portfolio.products]]` entries
- Set `share_target_ous` to the OUs you want to share with
- Each product's `launch_role_policies` declares the AWS managed policies its launch role needs

To create additional portfolios (e.g., admin vs. user), create a new TOML file in the same directory.

## Deployment

```bash
cd service-catalog

# Set up Python environment
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Bootstrap CDK (first time only, per account/region)
cdk bootstrap aws://ACCOUNT_ID/REGION

# Optional: validate before deploying
cdk synth

# Deploy all stacks (assets bucket + portfolio stacks)
cdk deploy --all
```

`cdk deploy --all` runs synthesis automatically, so `cdk synth` is optional — useful for catching config errors before hitting AWS.

## Post-Deployment: Grant Portfolio Access

After deployment, users need access to the portfolio. This is a manual step in the AWS Console:

1. Open **AWS Service Catalog** console in the hub account
2. Go to **Portfolios** → click your portfolio
3. Click the **Access** tab → **Grant access**
4. Select **Role** as the type
5. Enter the IAM Identity Center role pattern:
   ```
   AWSReservedSSO_ResearcherAccess*
   ```
   (Replace `ResearcherAccess` with your permission set name. The wildcard matches the SSO role suffix.)
6. Click **Grant access**

This grants access to all users with that Identity Center permission set. Repeat for additional permission sets as needed.

> **Future improvement**: Automated IDC assignment is planned as a future feature.

## Updating Products

To update a template: edit the YAML file in `templates/`, then `cdk deploy --all`. SC updates the product's provisioning artifact in place. Existing provisioned resources are unaffected.

To add a new product: add a `[[portfolio.products]]` entry to your portfolio TOML, then deploy.

To remove a product: remove it from the TOML and deploy. The product is disassociated from the portfolio. Existing provisioned resources continue running.

For side-by-side versions, create a new template file (e.g., `s3-research-bucket-v2.yaml`) and add it as a separate product.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Invalid hub_account` | Ensure 12-digit account ID in framework_config.yaml |
| `Invalid OU ID format` | Use format `ou-xxxxxxxxx-yyyyyyyyy` from AWS Organizations console |
| `cdk bootstrap` fails | Verify AWS credentials: `aws sts get-caller-identity` |
| `Template not found` | Check that product `template` paths in TOML are correct relative to `service-catalog/` |
| StackSet deployment fails | Verify hub account is delegated admin for CloudFormation StackSets |
| Portfolio not visible to users | Complete the post-deployment access grant steps above |
