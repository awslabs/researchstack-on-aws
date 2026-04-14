# ResearchStack on AWS — Service Catalog (CDK)

CDK project that deploys Service Catalog portfolios, products, launch roles, and OU sharing on top of the [CloudFormation templates](../templates/).

For deployment instructions and configuration reference, see the [Service Catalog Deployment Guide](../docs/service-catalog-guide.md). This README covers the code architecture for developers and contributors.

## How It Works

When you run `cdk deploy --all`, CDK executes `app.py`, which reads two config files (YAML + TOML), builds a tree of AWS resources in memory, synthesizes them into CloudFormation templates, and deploys them. The result is:

- An S3 bucket holding template artifacts (so spoke accounts can read them)
- A Service Catalog portfolio with products (one per CloudFormation template)
- Per-product IAM launch roles in the hub account
- StackSets that deploy those same launch roles into every account in the target OUs
- OU-level portfolio sharing so researchers in spoke accounts see the portfolio

## Folder Structure

```
service-catalog/
├── app.py                    # Entrypoint — orchestrates everything
├── framework_config.yaml     # Deployment settings (account, region, org, OUs)
├── cdk.json                  # CDK config (tells CDK to run app.py)
├── pyproject.toml            # Python dependencies and package config
├── portfolios/               # Portfolio TOML configs (one file = one portfolio)
├── core/                     # Config loaders — turn YAML/TOML into validated Python objects
├── stacks/                   # CDK stacks — the CloudFormation stacks that get deployed
├── sc_constructs/            # CDK constructs — reusable building blocks used by stacks
└── utils/                    # Shared helpers — naming, tagging, global config
```

## Call Flow

This is the order in which the code executes after you run `cdk deploy`:

```
cdk deploy --all
  │
  └─ CDK reads cdk.json → executes: python3 app.py
       │
       ├─ core/framework_config.py reads framework_config.yaml
       │    → validates account ID, region, org ID, OU formats
       │    → returns FrameworkConfig dataclass
       │
       ├─ utils/config.py stores env_name + project_slug as globals
       │
       ├─ stacks/assets_stack.py creates S3 bucket
       │    → org-wide read policy so spoke accounts can access templates
       │
       ├─ core/portfolio_config.py scans portfolios/*.toml
       │    → for each TOML: parses products, validates OUs against framework config
       │    → returns PortfolioConfig dataclass
       │
       ├─ stacks/portfolio_stack.py (one per portfolio TOML):
       │    ├─ creates SC Portfolio
       │    ├─ sc_constructs/portfolio_share.py shares with each target OU
       │    ├─ associates access_principals for automated portfolio access
       │    └─ for each product:
       │         ├─ creates SC CloudFormationProduct from template YAML
       │         ├─ sc_constructs/launch_role.py creates IAM role in hub account
       │         ├─ sets launch constraint (links role to product)
       │         └─ sc_constructs/stackset_factory.py deploys role to spoke accounts
       │              └─ sc_constructs/launch_role_stackset_template.py
       │                   (synthesizes a CFN template containing the same launch role)
       │
       ├─ utils/tagging.py applies standard tags to all stacks
       │
       └─ app.synth() generates CloudFormation JSON → CDK deploys to AWS
```

## Folder Details

### `core/` — Config Loaders

Turn config files into validated Python objects. CDK code never touches raw YAML/TOML — it works with the dataclasses these loaders return.

- `framework_config.py` — Reads `framework_config.yaml`. Returns a `FrameworkConfig` dataclass with deployment settings (account, region, org ID), available OUs, and tagging config. Validates all fields (12-digit account ID, valid region format, valid OU format). Raises `FrameworkConfigError` with a human-readable message + fix suggestion on any validation failure. Uses a module-level singleton so the config is loaded once and reused.

- `portfolio_config.py` — Reads TOML files from `portfolios/`. Each file becomes a `PortfolioConfig` dataclass containing portfolio metadata and a list of `ProductConfig` objects. Validates that target OUs are in the framework config's `available_ous` list (prevents sharing to unapproved OUs). `list_portfolios()` scans the directory to discover all TOML files — this is how `app.py` knows what to deploy without hardcoding portfolio names.

### `stacks/` — CDK Stacks (what gets deployed)

Each file produces one CloudFormation stack:

- `assets_stack.py` — Creates an S3 bucket for Service Catalog template artifacts. When a researcher launches a product, SC reads the template from this bucket. The bucket has an org-wide read policy (any account in the org can `GetObject`). One bucket shared across all portfolios. Deployed first because portfolio stacks depend on it.

- `portfolio_stack.py` — The main stack. Creates the SC portfolio, shares it with OUs, associates access principals, and for each product: creates the SC product from a template file, creates a launch role in the hub account, sets the launch constraint, and deploys the launch role to spoke accounts via a StackSet. The `_add_product()` method is where all per-product wiring happens.

### `sc_constructs/` — CDK Constructs (reusable building blocks)

Lower-level pieces that `portfolio_stack.py` assembles. These are CDK constructs — reusable components that encapsulate one piece of infrastructure.

- `launch_role.py` — Creates one IAM role per product. The role is assumed by `servicecatalog.amazonaws.com` when launching a product. Always includes `AWSCloudFormationFullAccess` (SC launches CFN stacks) plus whatever managed policies the product declares in the TOML. Also supports optional `custom_policy` inline statements for cases where AWS managed policies have gaps (e.g., `AmazonSageMakerFullAccess` excludes domain-level actions). Also includes an inline policy for reading SC template artifacts from S3. Role name follows the convention: `{slug}-{env}-{portfolio}-{product}-lc`.

- `portfolio_share.py` — Shares a portfolio with an OU using a CDK custom resource (Lambda-backed). CDK's built-in portfolio sharing doesn't support OU-level sharing with `share_tag_options` and `share_principals` flags, so this construct wraps the raw SC API calls (`createPortfolioShare`, `updatePortfolioShare`, `deletePortfolioShare`).

- `stackset_factory.py` — Creates CloudFormation StackSets that deploy launch roles to spoke accounts. Takes a `LaunchRoleStacksetProps`, synthesizes it into a CloudFormation template (by creating a temporary CDK app and calling `synth()`), then creates a `CfnStackSet` resource with that template body. Uses `SERVICE_MANAGED` permission model with `DELEGATED_ADMIN` for OU-based deployment. Auto-deployment is enabled so new accounts added to the OU automatically get the launch roles. Note: the factory also supports `SELF_MANAGED` account-based deployment (pass `target_accounts` instead of `target_ou_ids`), but this path isn't exposed in the portfolio TOML config yet — it's available for future use if institutions need to target specific accounts outside an OU structure.

- `launch_role_stackset_template.py` — A CDK stack that, when synthesized, produces a CloudFormation template containing a launch role. This template is what the StackSet deploys into spoke accounts. It reuses `LaunchRoleConstruct` — the same construct that creates the role in the hub account also generates the template for spoke accounts.

- `base_stackset_template.py` — Base class for stackset templates. Holds props and parameters. Exists as an extension point if we add other StackSet types in the future (e.g., TagOptions deployment).

### `utils/` — Shared Helpers

Stateless utilities used across the codebase:

- `config.py` — Global singleton holding `project_slug` (default `"rs"`) and `env_name` (default `"dev"`). These values get baked into every resource name as prefixes. Set once by `app.py` at startup, read by naming utilities throughout synthesis.

- `resource_naming.py` — Naming conventions for AWS resources:
  - `NameValidator` — regex validation for OU IDs and org IDs
  - `ResourceNaming` — sanitizes strings into valid AWS resource names (lowercase, replace special chars with hyphens)
  - `ServiceCatalogRoleNaming` — generates launch role and StackSet names: `{slug}-{env}-{portfolio}-{product}-lc`
  - `CloudFormationStackNaming` — generates stack names: `{slug}-{env}-{component}-stack`

- `tagging.py` — Walks the CDK construct tree and applies `Project`, `Environment`, and `DeployedBy` tags to every stack. Called once at the end of `app.py`.

### `cdk.json`

CDK's own config file. The key line is `"app": "python3 app.py"` — tells CDK how to run the app. The `context` section sets CDK feature flags (security defaults). You rarely edit this.

### `pyproject.toml`

Python package config (like `package.json` for npm). Declares dependencies (`aws-cdk-lib`, `PyYAML`) and which folders contain importable code. Read by `pip install -e .` to set up the development environment.

## Common Tasks

### Add a new product
1. Create the CloudFormation template in `templates/`
2. Add a `[[portfolio.products]]` entry to the portfolio TOML with `name`, `template`, and `launch_role_policies`. If AWS managed policies don't cover all required actions, add `[[portfolio.products.custom_policy]]` entries with the missing `actions` and `resources`.
3. Run `cdk deploy --all`

### Create a new portfolio
1. Create a new `.toml` file in `portfolios/` (copy `research-computing.toml` as a starting point)
2. Customize products, sharing targets, and access principals
3. Run `cdk deploy --all` — CDK auto-discovers the new TOML file

### Change the naming prefix
Run `cdk deploy --all -c project_slug=myorg` to override the default `rs` prefix. All resource names will use `myorg` instead.
