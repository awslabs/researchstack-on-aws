# ADR 0001: Service Catalog Simplification for ARC Toolkit

## Metadata
- **Status:** accepted
- **Date:** 2026-03-09
- **Subsystem:** service-catalog
- **Related:** Phase 2 implementation, SCAR codebase

## Context

The existing Service Catalog for Academic Research (SCAR) codebase provides a CDK-based deployment of AWS Service Catalog portfolios, products, and launch roles. It works, but carries complexity that isn't needed for the ARC Toolkit's goals. Phase 2 of ARC integrates Service Catalog as an optional governance layer on top of the CloudFormation templates built in Phase 1.

SCAR currently includes:
- Framework config system (YAML) + portfolio/product configs (TOML)
- Portfolio stack with OU sharing
- Product definitions supporting both CDK ProductStacks and raw CloudFormation files
- StackSet factory for deploying launch roles to target accounts
- Hub VPC module (~850 lines) with RAM sharing and SSM parameter distribution
- Service actions module (~850 lines) for SSM-based actions (restart EC2, attach EBS)
- Complex product versioning (products/ec2_instance/versions/v1/, v2/, v3/)
- Persona-based access control (not functional)

## Decision

Simplify SCAR into a focused Service Catalog deployment tool within the ARC monorepo. Specifically:

### Keep (working, necessary)
- **CDK framework** — handles state management, dependency ordering, and StackSet lifecycle
- **PortfolioStack** — portfolio creation, OU sharing via PortfolioShare construct
- **StacksetFactory** — launch role deployment to target accounts via CloudFormation StackSets
- **LaunchRoleConstruct** — IAM role creation for launch constraints
- **Framework config (YAML)** — deployment settings (hub account, region, org ID, OUs)
- **Portfolio config (TOML)** — portfolio definitions with product lists and sharing targets
- **Per-product launch roles** — one IAM role per product for least-privilege security

### Remove
- **Hub VPC module** — ARC templates handle their own VPC (create or accept existing). Institutions with centralized networking (Control Tower, LZA) pass VPC IDs directly. Future: provide Control Tower/LZA guidance in documentation.
- **Service actions** — not MVP. Can be added later if institutions request.
- **CDK ProductStack support** — ARC templates are raw CloudFormation YAML. No need for CDK-synthesized product templates.
- **Product versioning system** — the versions/v1/v2/v3 directory structure with per-version TOML configs is overkill. Products point directly at a template file. Version management happens through template file updates.
- **Persona system** — current admin/user persona mapping doesn't do anything functional. Portfolio access is configured manually via Identity Center. Future: document the manual process clearly.
- **Separate product directories** — instead of products/ec2_instance/config.toml with nested version dirs, product definitions live inline in the portfolio config.

### Change
- **Product configuration** — products defined inline in portfolio config rather than separate directories:
  ```toml
  [[portfolio.products]]
  name = "s3-research-bucket"
  template = "templates/storage/s3-research-bucket.yaml"
  launch_role_policies = ["AmazonS3FullAccess"]
  ```
- **Code location** — SC code moves into `aws-research-cloud/service-catalog/` (monorepo with templates)
- **Config format** — keep TOML for portfolio configs (flat key-value, works well, Python 3.11+ built-in parser), keep YAML for framework config (nested structures, consistency with AWS tooling)
- **Default example** — ship one example portfolio containing all ARC templates. Institutions customize/split as needed.

### Repo structure
```
aws-research-cloud/           # Monorepo: templates + service catalog
├── templates/                # CloudFormation templates (Phase 1, done)
├── service-catalog/          # CDK code for SC deployment (Phase 2)
├── docs/
├── ADRs/
└── README.md

arc-ai-assistant/             # Separate repo: GenAI/Quick Suite (Phase 3)
arc-cost-management/          # Separate repo: Cost tracking (Phase 4+)
```

Rationale for monorepo: templates and SC config are tightly coupled (adding a template means adding it to a portfolio; changing template parameters may require launch role updates). They should version together. GenAI and cost management have different deployment lifecycles, dependencies, and audiences — they belong in separate repos.

## Alternatives Considered

### 1. Rewrite from scratch (boto3 instead of CDK)
Rejected. CDK handles StackSet lifecycle, dependency ordering, and drift detection. Reimplementing this in boto3 would be significant effort for no benefit. The complexity in SCAR isn't CDK — it's the optional modules and config system.

### 2. Keep all SCAR features, just reorganize
Rejected. Hub VPC and service actions add ~1,700 lines of code and operational complexity that most institutions won't use. Better to ship lean and add back if requested.

### 3. Single config format (all YAML or all TOML)
Considered but rejected. Switching working config parsers is churn with no user benefit. YAML suits the nested framework config; TOML suits the flat portfolio configs. Users touch these once during setup.

### 4. Shared launch role per portfolio (instead of per-product)
Rejected. Per-product roles follow least-privilege. An S3 product shouldn't have EC2 permissions. The StackSet overhead is manageable since CDK handles the lifecycle.

## Consequences

### Positive
- ~70% code reduction (estimated ~1,500 lines from ~5,000+)
- Simpler onboarding for institutions
- Templates and SC config ship together (atomic updates)
- Clear separation: tightly coupled (monorepo) vs loosely coupled (separate repos)

### Negative
- Institutions wanting Hub VPC must set it up independently (mitigated by future documentation)
- No service actions out of the box (can be added later)
- Product versioning is manual (update template file, redeploy)

### Future considerations
- Document Control Tower / LZA integration guidance for institutions with centralized networking
- Add service actions if multiple institutions request them
- Consider portfolio access automation if manual Identity Center setup proves painful
