# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Governance budget alert template (`templates/governance/budget-alert.yaml`) — monthly budget tracking by CostCenter tag with email notifications at 50%, 80%, 100% forecasted, and 100% actual thresholds
- Cost allocation tag activation guide in cost optimization docs
- Service Catalog developer guide (`service-catalog/README.md`) — code architecture, call flow, folder details
- Configuration reference in Service Catalog deployment guide — all framework and portfolio config fields documented
- ADR 0007: Cost governance strategy (budgets, idle shutdown, enforcement)

### Changed
- CONTRIBUTING.md updated to match current template conventions (removed stale metadata references)
- Cost optimization guide expanded with budget alert deployment instructions
- Research lifecycle guide updated with FSx Lustre and budget alert in decision matrix
- Templates README updated with governance category and FSx Lustre

### Removed
- Empty `examples/` and `scripts/` placeholder directories

## [0.1.0] - 2026-03-09

### Added
- Initial repository structure with templates-first organization
- CloudFormation templates: S3, EFS, FSx Lustre, EC2 (4 variants), ParallelCluster, SageMaker Studio, Research VPC
- Service Catalog CDK project with portfolio management, launch roles, StackSets, and OU sharing
- Documentation: deployment guide, ParallelCluster guide, research lifecycle guide, cost optimization guide
- ADRs 0001-0006 documenting architectural decisions
