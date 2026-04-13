# Service Catalog Deployment Guide

This guide walks through deploying the ResearchStack's Service Catalog layer, which adds portfolio-based governance, OU sharing, and per-product launch roles on top of the CloudFormation templates. It follows a hub-and-spoke model: one central account (the hub) manages portfolios and shares them out to researcher accounts (spokes) across your organization. It's intended for IT admins or cloud teams setting up governed self-service for researchers across multiple AWS accounts.

## Architecture

<!-- TODO: Add Service Catalog architecture diagram -->
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
  - OU evolution note: Institutions typically start with a single "Research" OU, then split over time
    into purpose-specific OUs (e.g., Research-Sandbox, Research-HIPAA, Research-Production).
    The SC layer supports sharing to multiple OUs — just add them to share_target_ous in the portfolio TOML.
  - IDC note: Recommend IAM Identity Center as the default identity approach.
    Two starting permission sets: AWSServiceCatalogEndUserAccess (researchers) and
    AdministratorAccess (IT admins). IDC permission sets auto-create matching IAM roles
    in every assigned account, enabling automated principal sharing via access_principals in the TOML.
-->

## Why CDK?

The Service Catalog layer uses CDK as its infrastructure-as-code tool (with Python as the language). Here's why CDK over raw CloudFormation or boto3 scripts:

- StackSets for launch roles require lifecycle management (create, update, delete across accounts)
- Portfolio → product → launch role → StackSet dependencies need ordering
- CDK handles drift detection and state tracking automatically

You don't need to know CDK to use this — just edit config files and run `cdk deploy`.

## Key Concepts

Quick reference for the AWS services involved in this deployment:

- **AWS Organizations** — Central management of multiple AWS accounts. Provides the OU structure that Service Catalog shares portfolios into, and that StackSets deploy launch roles across.
- **Service Catalog** — Lets IT publish approved CloudFormation templates as "products" in a "portfolio." Researchers browse and launch products without needing CloudFormation knowledge.
- **Portfolio** — A collection of products shared to specific OUs. Controls who can launch what.
- **Product** — A single CloudFormation template wrapped for Service Catalog consumption.
- **Launch Role** — An IAM role that Service Catalog assumes when provisioning a product. Scoped per-product so each template gets only the permissions it needs (least privilege).
- **StackSets** — Deploys the same CloudFormation template (in this case, launch roles) across multiple accounts in an OU automatically.
- **Delegated Administrator** — An Organizations feature that lets a non-management account (the hub) administer Service Catalog and StackSets on behalf of the org.

## Prerequisites

Before deploying, you need three things set up in AWS and a few tools installed locally.

### AWS Account Setup

1. **AWS Organizations enabled** — Service Catalog OU sharing and StackSets both require Organizations. If you haven't set this up yet, see [AWS Organizations Getting Started](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started.html).

2. **A designated hub account as delegated administrator** — Pick one account (not the management account) to host your Service Catalog portfolios. This hub account needs delegated admin for both Service Catalog and CloudFormation StackSets. Run these from the **management account**:
   ```bash
   # Delegate Service Catalog admin to hub account
   aws organizations register-delegated-administrator \
     --account-id HUB_ACCOUNT_ID \
     --service-principal servicecatalog.amazonaws.com

   # Enable StackSets service access across the org
   aws organizations enable-aws-service-access \
     --service-principal member.org.stacksets.cloudformation.amazonaws.com
   ```

3. **Target OU IDs identified** — Know which OUs contain the accounts where researchers will consume templates. You can find OU IDs in the [AWS Organizations console](https://console.aws.amazon.com/organizations/) — they look like `ou-xxxx-xxxxxxxx`. We recommend starting with a single "Research" OU. As your organization scales, you can split into purpose-specific OUs (e.g., Research-Sandbox, Research-HIPAA). See [Organizing Your AWS Environment](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/organizing-your-aws-environment.html) for best practices, and consider [Landing Zone Accelerator](https://aws.amazon.com/solutions/implementations/landing-zone-accelerator-on-aws/) or [Secure Research Environment](https://aws.amazon.com/solutions/implementations/secure-research-environment-on-aws/) for compliance-heavy setups.

### Local Tools

The ResearchStack's Service Catalog layer is a CDK project written in Python. You'll need:

- **Python 3.11+** — CDK dependency. Install via [python.org](https://www.python.org/downloads/) or your system package manager.
- **Node.js 18+** — Required by the CDK CLI runtime. Install via [nodejs.org](https://nodejs.org/).
- **AWS CDK CLI** — Install globally after Node.js: `npm install -g aws-cdk`
- **AWS CLI** — Install via [AWS CLI docs](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), then configure credentials for the hub account: `aws configure sso` for [IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html) (recommended) or `aws configure` for [IAM access keys](https://docs.aws.amazon.com/cli/latest/userguide/cli-authentication-user.html).

Verify everything is ready:
```bash
python3 --version            # 3.11+
node --version               # 18+
cdk --version                # 2.x
aws --version                # 2.x
aws sts get-caller-identity [--profile your-profile-name]  # should show your hub account ID (use --profile only when explicitly naming your profile for login)
```

## Configuration

Two config files control what gets deployed and where. Edit these before running `cdk deploy`.

### 1. Framework Config (`service-catalog/framework_config.yaml`)

Sets your deployment target — which account, region, and org to deploy into:
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

Each TOML file defines a portfolio with inline products. The example `research-computing.toml` includes all templates. Customize it:

- Add/remove products by editing `[[portfolio.products]]` entries
- Set `share_target_ous` to the OUs you want to share with
- Set `access_principals` to grant portfolio access automatically (see [Granting Portfolio Access](#granting-portfolio-access) below)
- Each product's `launch_role_policies` declares the AWS managed policies its launch role needs

To create additional portfolios (e.g., admin vs. user), create a new TOML file in the same directory.

## Configuration Reference

Complete reference for every configurable field. Fields marked (required) must be set before deploying.

### Framework Config Fields (`framework_config.yaml`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `deployment.hub_account` | String | Yes | — | 12-digit AWS account ID for the hub account where SC resources are deployed |
| `deployment.hub_region` | String | Yes | — | AWS region for deployment (e.g., `us-east-1`) |
| `deployment.organization_id` | String | Yes | — | AWS Organization ID (format: `o-xxxxxxxxxx`). Used for S3 bucket org-wide read policy |
| `deployment.default_env_name` | String | No | `dev` | Environment name baked into resource names (e.g., `dev`, `staging`, `prod`) |
| `available_ous` | List of strings | Yes | — | OU IDs that portfolios are allowed to share to. Portfolio TOML `share_target_ous` are validated against this list. Format: `ou-xxxx-xxxxxxxx` |
| `tagging.required_tags` | Map | No | `{}` | Key-value pairs applied as tags to all CDK-managed stacks |

### Portfolio Config Fields (`portfolios/*.toml`)

**Portfolio section (`[portfolio]`):**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | String | Yes | — | Machine identifier for the portfolio (used in stack names, no spaces) |
| `display_name` | String | Yes | — | Human-readable name shown in the SC console |
| `description` | String | No | `""` | Portfolio description shown in the SC console |
| `provider_name` | String | No | `"ResearchStack on AWS"` | Organization name shown as the portfolio provider |
| `support_email` | String | No | `""` | Support email shown on all products in this portfolio |
| `support_url` | String | No | `""` | Support URL shown on all products |
| `support_description` | String | No | `""` | Support description text shown on all products |
| `distributor` | String | No | `""` | Distributor name shown on all products |
| `share_target_ous` | List of strings | Yes | — | OU IDs to share this portfolio with. Must be listed in `framework_config.yaml` `available_ous` |
| `access_principals` | List of strings | No | `[]` | IAM principal ARN patterns for automated portfolio access. Supports wildcards. See [Granting Portfolio Access](#granting-portfolio-access) |
| `share_tag_options` | Boolean | No | `true` | Whether to share TagOptions with spoke accounts when sharing the portfolio |
| `share_principals` | Boolean | No | `true` | Whether to propagate `access_principals` to spoke accounts via principal sharing |

**Product entries (`[[portfolio.products]]`):**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | String | Yes | — | Machine identifier (used for IAM role names, StackSet names — no spaces, alphanumeric + hyphens) |
| `display_name` | String | No | Derived from `name` | Human-readable name shown in the SC console |
| `description` | String | No | `""` | Product description shown in the SC console |
| `template` | String | Yes | — | Relative path to the CloudFormation template (relative to `service-catalog/`, e.g., `../templates/storage/s3-research-bucket.yaml`) |
| `launch_role_policies` | List of strings | No | `[]` | AWS managed policy names for the launch role (e.g., `AmazonS3FullAccess`). `AWSCloudFormationFullAccess` is always added automatically |

## Deployment

Once config files are set, deploy from the `service-catalog/` directory. CDK will create the assets bucket, portfolio, products, launch roles, and StackSets. Add `--profile your-profile-name` to CDK commands if you're using named AWS CLI profiles.

```bash
cd service-catalog

# Set up Python environment (isolates CDK library + project dependencies from your global Python)
python3 -m venv .venv
source .venv/bin/activate
pip install -e .  # installs aws-cdk-lib, constructs, and project dependencies from pyproject.toml

# Bootstrap CDK (first time only, per account/region)
cdk bootstrap aws://ACCOUNT_ID/REGION [--profile your-profile-name]

# Optional: validate before deploying
cdk synth [--profile your-profile-name]

# Deploy all stacks (assets bucket + portfolio stacks)
cdk deploy --all [--profile your-profile-name]
```

`cdk deploy --all` runs synthesis automatically, so `cdk synth` is optional — useful for catching config errors before hitting AWS.

## Granting Portfolio Access

Researchers need access to the portfolio before they can launch products. The recommended approach is to define principal ARN patterns in your portfolio TOML — this grants access automatically in the hub account and propagates to all spoke accounts via principal sharing.

### Recommended: Automated via TOML Config

Add `access_principals` to your portfolio TOML with IAM principal ARN patterns. Wildcards are supported, which is especially useful for IDC roles where the suffix varies per IDC instance.

This approach works when the specified roles exist across all spoke accounts that receive the portfolio share. IDC [permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html) automatically create matching IAM roles in every assigned account, making them a natural fit. Standard IAM roles work too, as long as they're provisioned consistently across accounts (e.g., via StackSets or CloudFormation).

```toml
access_principals = [
    "arn:aws:iam:::role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_AdministratorAccess*",
    "arn:aws:iam:::role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_AWSServiceCatalogEndUserAccess*"
]
```

Then run `cdk deploy --all`. Service Catalog associates these patterns with the portfolio and — because `share_principals = true` — automatically grants access to matching roles in every spoke account that receives the portfolio share. No manual steps per account.

**ARN format differs between IDC and IAM roles:**

| Role type | ARN pattern |
|-----------|-------------|
| IDC (Identity Center) | `arn:aws:iam:::role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_PermissionSetName*` |
| Standard IAM role | `arn:aws:iam:::role/RoleName` |
| All roles (broad access) | `arn:aws:iam:::role/*` |

IDC roles live under the `aws-reserved/sso.amazonaws.com/` path in IAM — this must be included in the ARN pattern. Standard IAM roles sit directly under `role/`. The `*` wildcard matches any suffix, including the IDC instance ID that gets appended to permission set names.

### Alternative: Manual Console Grant

For one-off access grants or spoke-account-specific overrides, you can grant access manually:

1. Open **AWS Service Catalog** console in the target account
2. Go to **Portfolios** → click your portfolio (or **Imported** in spoke accounts)
3. Click the **Access** tab → **Grant access**
4. Select the principal type and enter the role name or ARN
5. Click **Grant access**

## Updating Products

How to manage templates after initial deployment.

- **Update a template**: Edit the YAML file in `templates/`, then `cdk deploy --all`. SC updates the product's provisioning artifact in place. Existing provisioned resources are unaffected.
- **Add a new product**: Add a `[[portfolio.products]]` entry to your portfolio TOML, then deploy.
- **Remove a product**: Remove it from the TOML and deploy. The product is disassociated from the portfolio. Existing provisioned resources continue running.
- **Side-by-side versions**: Create a new template file (e.g., `s3-research-bucket-v2.yaml`) and add it as a separate product.

## Troubleshooting

Common issues and how to resolve them.

| Issue | Solution |
|-------|----------|
| `Invalid hub_account` | Ensure 12-digit account ID in framework_config.yaml |
| `Invalid OU ID format` | Use format `ou-xxxxxxxxx-yyyyyyyyy` from AWS Organizations console |
| `cdk bootstrap` fails | Verify AWS credentials: `aws sts get-caller-identity` |
| `Template not found` | Check that product `template` paths in TOML are correct relative to `service-catalog/` |
| StackSet deployment fails | Verify hub account is delegated admin for CloudFormation StackSets |
| Portfolio not visible to users | Check `access_principals` in your portfolio TOML — see [Granting Portfolio Access](#granting-portfolio-access) |
| Portfolio not visible in spoke accounts | Ensure OU IDs are uncommented in `share_target_ous` in your portfolio TOML and redeploy |
