# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- EC2 idle shutdown — CloudWatch alarm auto-stops instances after configurable idle period (CPU < 5%). Default 2 hours, user-configurable 15 min to 24 hours. Enabled by default on all EC2 templates.
- EC2 custom AMI support — optional `CustomAmiId` parameter on all EC2 templates overrides the default OS/AMI selection. Use for golden AMIs with pre-installed software.
- EC2 Spot pricing — `PricingModel` parameter (on-demand/spot) on all EC2 templates. Persistent Spot with stop-on-interruption preserves EBS data.
- EC2 Spot Fleet template (`ec2-spot-fleet.yaml`) — cost-optimized Spot across multiple instance generations and AZs. Pick a family and size, fleet picks the best pool.
- EC2 start/stop commands in stack outputs — researchers can restart stopped instances without IT help
- ParallelCluster `AllowedIps` parameter (renamed from `DCVAllowedIps`) — controls both SSH and DCV access. Required when key pair or DCV is enabled (CloudFormation Rules validation).
- cdk-nag integrated into pytest suite (4 tests, AwsSolutions checks with documented suppressions)
- ASH config (`.ash/.ash.yaml`) — disabled redundant scanners, added ignore paths

### Changed
- Custom inline policy support (`custom_policy`) for Service Catalog launch roles — use when AWS managed policies have gaps (e.g., `AmazonSageMakerFullAccess` excludes domain-level tagging actions)

### Fixed
- SageMaker Studio: launch role now uses `sagemaker:*` custom policy instead of `AmazonSageMakerFullAccess`, which excludes domain/user-profile/app/space resources via `NotResource`
- ParallelCluster: renamed `DCVSecretsPolicy` from `pcluster-` to `parallelcluster-` prefix to match the PCluster provider's IAM policy allowlist
- ParallelCluster: bumped provider from 3.14.0 to 3.15.0 to fix CloudWatch alarm tagging permission error (`UnauthorizedTaggingOperation`) caused by stricter CloudFormation tag enforcement

### Added
- Governance budget alert template (`templates/governance/budget-alert.yaml`) — monthly budget tracking by CostCenter tag with email notifications at 50%, 80%, 100% forecasted, and 100% actual thresholds
- ADR 0007: Cost governance strategy (budgets, idle shutdown, enforcement)
- 80 unit tests at 98% coverage (config loaders, utils, CDK stack synthesis)
- GitHub Actions CI workflow (cfn-lint on templates + pytest on service catalog code)
- Repo hygiene files: CODE_OF_CONDUCT, SECURITY, CHANGELOG, SUPPORT
- GitHub templates: PR template, issue templates (bug report, feature request)
- Service Catalog developer guide (`service-catalog/README.md`) — code architecture, call flow, folder details
- Configuration reference in Service Catalog deployment guide — all framework and portfolio config fields documented
- "Verify Your Deployment" checklist in Service Catalog deployment guide
- Cost allocation tag activation guide in cost optimization docs
- F&A and Cloud Computing section in cost optimization guide (P.L. 119-75, Feb 2026)
- "Getting Started" section in templates README (VPC-first flow, LZA/Control Tower note)
- Cloud Intelligence Dashboards reference for cross-org cost reporting
- AWS Open Data Sponsorship Program reference in research lifecycle guide

### Changed
- Main README rewritten — punchier intro, templates table, simplified quick start, CFN console link
- Research lifecycle guide rewritten — full phase coverage, template mapping per phase, on-prem guidance, collaboration considerations
- Cost optimization guide overhauled — links throughout, Savings Plans detail, Spot guidance, idle shutdown, SageMaker auto-stop, Data Exports recommendation, research phase strategies expanded
- Service Catalog deployment guide rewritten — architecture section with linked definitions, CDK mapping table, CloudShell for delegation commands, TagOptions/share_principals explained, least privilege guidance
- Access control guidance: recommend account-level isolation as primary boundary, IDC permission sets for role assignment
- CONTRIBUTING.md updated to match current template conventions
- ParallelCluster: removed default ClusterName (prevents conflicts), improved description
- Parameter validation added across all templates (EFS IDs, S3 bucket names, S3 ARNs, instance type regex anchors, DCV CIDR/password, Capacity Block IDs)
- SageMaker Studio: Owner parameter made optional (was required, inconsistent with other templates)
- Project slug standardized to `rs` throughout (was `arc` in some places)
- All doc cross-references verified and fixed (removed stale ec2-hpc-optimized references, added FSx Lustre, governance category)

### Removed
- Empty `examples/` and `scripts/` placeholder directories
- ASH scan artifacts from git tracking

## [0.1.0] - 2026-03-09

### Added
- Initial repository structure with templates-first organization
- CloudFormation templates: S3, EFS, FSx Lustre, EC2 (4 variants), ParallelCluster, SageMaker Studio, Research VPC
- Service Catalog CDK project with portfolio management, launch roles, StackSets, and OU sharing
- Documentation: deployment guide, ParallelCluster guide, research lifecycle guide, cost optimization guide
- ADRs 0001-0006 documenting architectural decisions
