# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
