# Service Catalog Deployment Guide

Deploy governed, self-service research computing across multiple AWS accounts. Researchers browse a catalog and click "Launch" — no CloudFormation knowledge needed. IT admins control what's available, who can launch it, and what permissions each product gets.

This guide walks through setting up the [AWS Service Catalog](https://aws.amazon.com/servicecatalog/) layer on top of ResearchStack's CloudFormation templates. It follows a hub-and-spoke model: one central account manages portfolios and shares them to researcher accounts across your organization.

## Architecture

The Service Catalog layer adds governance on top of the same templates you can deploy standalone. Here's how the pieces fit together:

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
    - OUs contain spoke accounts (e.g., ou-xxxx-research, ou-yyyy-sandbox)
  - Flow: CDK deploy → Assets Bucket + Portfolio + StackSets → OU Share → Spoke users see portfolio → Provision product → Launch role scopes permissions → CFN creates tagged resources
  - IDC note: Recommend IAM Identity Center as the default identity approach.
    Two starting permission sets: AWSServiceCatalogEndUserAccess (researchers) and
    AdministratorAccess (IT admins). IDC permission sets auto-create matching IAM roles
    in every assigned account, enabling automated principal sharing via access_principals in the TOML.
-->

**Hub account** — A designated AWS account (not the management account) where [CDK](https://aws.amazon.com/cdk/) deploys the Service Catalog portfolio, products, and an S3 bucket for template artifacts. This account is registered as a [delegated administrator](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_integrate_services_list.html) for Service Catalog and CloudFormation StackSets, so it can manage resources across the organization without using the management account (which should be reserved for billing and Organizations administration only).

**Portfolio** — A collection of products (templates) shared to specific [Organizational Units (OUs)](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_ous.html). Controls who can launch what. Defined in a TOML config file.

**Products** — Each ResearchStack CloudFormation template wrapped for Service Catalog. Researchers see a product name, description, and a "Launch" button — they fill in parameters and get their resources.

**Launch roles** — Per-product IAM roles that Service Catalog assumes when creating resources on behalf of a researcher. Each product gets only the permissions it needs (e.g., the S3 product gets `AmazonS3FullAccess`, not admin access). Created in the hub account by CDK, then deployed to every spoke account via [CloudFormation StackSets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html).

**StackSets** — CloudFormation's built-in mechanism for deploying the same template to multiple accounts. Here, they push launch roles into every account in the target OUs. When a new account is added to an OU, the launch role is deployed automatically.

**OU sharing** — The portfolio is shared at the OU level, so every account in the OU sees it. Researchers in spoke accounts browse the shared portfolio and launch products using the launch roles that StackSets deployed into their account.

## Why CDK?

The Service Catalog layer uses [AWS CDK](https://aws.amazon.com/cdk/) (Cloud Development Kit) with Python as the infrastructure-as-code tool. CDK generates CloudFormation templates from Python code, giving us:

| What CDK handles | Where we use it |
|---|---|
| Dependency ordering | Portfolio → products → launch roles → StackSets must deploy in sequence |
| StackSet lifecycle | Creating, updating, and deleting launch roles across accounts |
| State tracking | CDK knows what's deployed and only changes what's different |
| Asset management | Uploads template files to S3 automatically |

You don't need to know CDK or Python to use this — just edit config files and run `cdk deploy`. For code architecture details, see the [Service Catalog Developer Guide](../service-catalog/README.md).

## Prerequisites

### AWS Account Setup

1. **[AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_getting-started.html) enabled** — Service Catalog OU sharing and StackSets both require Organizations.

2. **A hub account registered as delegated administrator** — Pick one account (not the management account — the management account should be reserved for billing and Organizations administration, not workload deployment). Run these from the **management account**:
   ```bash
   # Delegate Service Catalog admin to hub account
   aws organizations register-delegated-administrator \
     --account-id HUB_ACCOUNT_ID \
     --service-principal servicecatalog.amazonaws.com

   # Enable StackSets service access across the org
   aws organizations enable-aws-service-access \
     --service-principal member.org.stacksets.cloudformation.amazonaws.com
   ```

3. **Target OU IDs identified** — Know which OUs contain the accounts where researchers will consume templates. Find OU IDs in the [AWS Organizations console](https://console.aws.amazon.com/organizations/) — they look like `ou-xxxx-xxxxxxxx`. Start with a single "Research" OU. As your organization scales, you can split into purpose-specific OUs (e.g., Research-Sandbox, Research-HIPAA). See [Organizing Your AWS Environment](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/organizing-your-aws-environment.html) for best practices, and consider [Landing Zone Accelerator](https://aws.amazon.com/solutions/implementations/landing-zone-accelerator-on-aws/) for compliance-heavy setups.

### Local Tools

- **Python 3.11+** — [python.org](https://www.python.org/downloads/) or your system package manager
- **Node.js 18+** — Required by the CDK CLI. [nodejs.org](https://nodejs.org/)
- **AWS CDK CLI** — `npm install -g aws-cdk` (after Node.js is installed)
- **AWS CLI** — [Install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). Configure credentials for the hub account: `aws configure sso` for [IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html) (recommended) or `aws configure` for [access keys](https://docs.aws.amazon.com/cli/latest/userguide/cli-authentication-user.html). Alternatively, run CLI commands from [AWS CloudShell](https://aws.amazon.com/cloudshell/) in the console — no local install needed.

Verify:
```bash
python3 --version            # 3.11+
node --version               # 18+
cdk --version                # 2.x
aws sts get-caller-identity  # should show your hub account ID
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
  - "ou-xxxx-xxxxxxxx"  # Approved OUs that portfolios can share to
```

The `available_ous` list acts as a guardrail — portfolio configs can only share to OUs listed here. This prevents accidental sharing to the wrong OU (a typo in a portfolio TOML would be caught at synthesis time, not at deploy time with a cryptic StackSet error).

### 2. Portfolio Config (`service-catalog/portfolios/*.toml`)

Each TOML file defines a portfolio with inline products. The example `research-computing.toml` includes all templates. Customize it:

- Add/remove products by editing `[[portfolio.products]]` entries
- Set `share_target_ous` to the OUs you want to share with
- Set `access_principals` to grant portfolio access automatically (see [Granting Portfolio Access](#granting-portfolio-access) below)
- Each product's `launch_role_policies` declares the AWS managed policies its launch role needs

To create additional portfolios (e.g., separate catalogs for different departments), create a new TOML file in the same directory.

## Configuration Reference

Complete reference for every configurable field. Fields marked (required) must be set before deploying.

### Framework Config Fields (`framework_config.yaml`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `deployment.hub_account` | String | Yes | — | 12-digit AWS account ID for the hub account |
| `deployment.hub_region` | String | Yes | — | AWS region for deployment (e.g., `us-east-1`) |
| `deployment.organization_id` | String | Yes | — | AWS Organization ID (format: `o-xxxxxxxxxx`). Used for S3 bucket org-wide read policy |
| `deployment.default_env_name` | String | No | `dev` | Environment name baked into resource names (e.g., `dev`, `staging`, `prod`) |
| `available_ous` | List of strings | Yes | — | OU IDs that portfolios are allowed to share to. Format: `ou-xxxx-xxxxxxxx` |
| `tagging.required_tags` | Map | No | `{}` | Key-value pairs applied as tags to all CDK-managed stacks |

### Portfolio Config Fields (`portfolios/*.toml`)

**Portfolio section (`[portfolio]`):**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | String | Yes | — | Machine identifier (used in stack names, no spaces) |
| `display_name` | String | Yes | — | Human-readable name shown in the [SC console](https://console.aws.amazon.com/servicecatalog/) |
| `description` | String | No | `""` | Portfolio description shown in the SC console |
| `provider_name` | String | No | `"ResearchStack on AWS"` | Organization name shown as the portfolio provider |
| `support_email` | String | No | `""` | Support email shown on all products |
| `support_url` | String | No | `""` | Support URL shown on all products |
| `support_description` | String | No | `""` | Support description text shown on all products |
| `distributor` | String | No | `""` | Distributor name shown on all products |
| `share_target_ous` | List of strings | Yes | — | OU IDs to share this portfolio with. Must be in `framework_config.yaml` `available_ous` |
| `access_principals` | List of strings | No | `[]` | IAM principal ARN patterns for automated portfolio access. Supports wildcards. See [Granting Portfolio Access](#granting-portfolio-access) |
| `share_tag_options` | Boolean | No | `true` | Share TagOptions with spoke accounts |
| `share_principals` | Boolean | No | `true` | Propagate `access_principals` to spoke accounts |

**Product entries (`[[portfolio.products]]`):**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | String | Yes | — | Machine identifier (used for IAM role names, StackSet names — alphanumeric + hyphens) |
| `display_name` | String | No | Derived from `name` | Human-readable name in the SC console |
| `description` | String | No | `""` | Product description in the SC console |
| `template` | String | Yes | — | Relative path to the CloudFormation template (e.g., `../templates/storage/s3-research-bucket.yaml`) |
| `launch_role_policies` | List of strings | No | `[]` | AWS managed policy names for the launch role. `AWSCloudFormationFullAccess` is always added automatically |

## Deployment

Deploy from the `service-catalog/` directory. CDK creates the assets bucket, portfolio, products, launch roles, and StackSets. Add `--profile your-profile-name` to CDK commands if using named AWS CLI profiles. You can also run these commands from [AWS CloudShell](https://aws.amazon.com/cloudshell/) if you prefer not to install tools locally.

```bash
cd service-catalog

# Set up Python environment
python3 -m venv .venv
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

## Granting Portfolio Access

Researchers need access to the portfolio before they can launch products. The recommended approach is to define principal ARN patterns in your portfolio TOML — this grants access automatically in the hub account and propagates to all spoke accounts via principal sharing.

### Recommended: Automated via TOML Config

Add `access_principals` to your portfolio TOML with IAM principal ARN patterns. Wildcards are supported, which is useful for [IAM Identity Center](https://aws.amazon.com/iam/identity-center/) roles where the suffix varies per IDC instance.

This works when the specified roles exist across all spoke accounts. IDC [permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html) automatically create matching IAM roles in every assigned account, making them a natural fit.

```toml
access_principals = [
    "arn:aws:iam:::role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_AdministratorAccess*",
    "arn:aws:iam:::role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_AWSServiceCatalogEndUserAccess*"
]
```

Then run `cdk deploy --all`. Service Catalog associates these patterns with the portfolio and — because `share_principals = true` — automatically grants access to matching roles in every spoke account.

**ARN format:**

| Role type | ARN pattern |
|-----------|-------------|
| IDC (Identity Center) | `arn:aws:iam:::role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_PermissionSetName*` |
| Standard IAM role | `arn:aws:iam:::role/RoleName` |

IDC roles live under the `aws-reserved/sso.amazonaws.com/` path — this must be included in the ARN pattern.

### Alternative: Manual Console Grant

For one-off access or spoke-account-specific overrides:

1. Open the [Service Catalog console](https://console.aws.amazon.com/servicecatalog/) in the target account
2. Go to **Portfolios** → click your portfolio (or **Imported** in spoke accounts)
3. Click **Access** → **Grant access**
4. Select the principal type and enter the role name or ARN

## Updating Products

- **Update a template**: Edit the YAML file in `templates/`, then `cdk deploy --all`. Existing provisioned resources are unaffected.
- **Add a new product**: Add a `[[portfolio.products]]` entry to your portfolio TOML, then deploy.
- **Remove a product**: Remove it from the TOML and deploy. Existing provisioned resources continue running.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Invalid hub_account` | Ensure 12-digit account ID in framework_config.yaml |
| `Invalid OU ID format` | Use format `ou-xxxxxxxxx-yyyyyyyyy` from [Organizations console](https://console.aws.amazon.com/organizations/) |
| `cdk bootstrap` fails | Verify AWS credentials: `aws sts get-caller-identity` |
| `Template not found` | Check that product `template` paths in TOML are correct relative to `service-catalog/` |
| StackSet deployment fails | Verify hub account is [delegated admin](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_integrate_services_list.html) for CloudFormation StackSets |
| Portfolio not visible to users | Check `access_principals` in your portfolio TOML — see [Granting Portfolio Access](#granting-portfolio-access) |
| Portfolio not visible in spoke accounts | Ensure OU IDs are in `share_target_ous` in your portfolio TOML and redeploy |
