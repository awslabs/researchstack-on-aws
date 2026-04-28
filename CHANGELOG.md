# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- EC2 idle shutdown — CloudWatch alarm auto-stops instances after configurable idle period (CPU < 5%). Default 2 hours, user-configurable 15 min to 24 hours. Enabled by default on all EC2 templates.
- EC2 custom AMI support — optional `CustomAmiId` parameter on all EC2 templates and ParallelCluster. Use for golden AMIs with pre-installed software.
- EC2 Spot pricing — `PricingModel` parameter (on-demand/spot) on all EC2 templates. Persistent Spot with stop-on-interruption preserves EBS data.
- EC2 Spot Fleet template (`ec2-spot-fleet.yaml`) — cost-optimized Spot across multiple instance generations and AZs
- EC2 S3 Files shared storage auto-created by default — mounted at `/mnt/s3files` (~$0.023/GB/month). Set `AutoCreateStorage` to `none` to opt out.
- EC2 IMDSv2 enforced on all instances and launch templates
- EC2 start/stop commands in stack outputs
- ParallelCluster `AllowedIps` parameter (renamed from `DCVAllowedIps`) — controls both SSH and DCV access
- Governance budget alert template (`templates/governance/budget-alert.yaml`) — monthly budget tracking by CostCenter tag with email notifications at 50%, 80%, and 100% thresholds
- Deploy helper script (`deploy.sh`) — deploys from parameter files with `--dry-run` support
- Per-template parameter files (`params/`) — 10 configs with AWS resource lookup commands in README
- Researcher IAM policy (`examples/researcher-policy.json`) — least-privilege policy for SC end users, SSM, S3, Cost Explorer
- Service Catalog architecture diagram
- TagOptions enforcement guide in Service Catalog deployment guide
- Custom AMI guide in templates README

### Changed
- IAMFullAccess removed from 7 of 8 Service Catalog launch roles — replaced with scoped least-privilege policies. PCluster retains IAMFullAccess (provider manages IAM internally).
- S3 auto-created buckets use DeletionPolicy Delete (non-empty buckets are protected natively by CloudFormation)
- Idle shutdown no longer stops instances prematurely on fresh launches
- EC2 parameter groups reorganized — Storage group with all storage options, Advanced group for power-user settings
- ParallelCluster parameter groups reorganized — Cluster Configuration, Networking, Access, Storage, Advanced
- Documentation overhauled — main README, templates README, FAQ, cost optimization guide, research lifecycle guide, Service Catalog guide

### Fixed
- SageMaker Studio launch role scoped to `sagemaker:*` custom policy
- ParallelCluster DCV secrets policy prefix corrected
- SSH key pair descriptions note public subnet requirement

### Added (earlier)
- Governance budget alert template — monthly budget tracking by CostCenter tag
- Cost allocation tag activation guide in cost optimization docs
- F&A and Cloud Computing section in cost optimization guide (P.L. 119-75, Feb 2026)
- AWS Open Data Sponsorship Program reference in research lifecycle guide

### Changed (earlier)
- Documentation overhauled — research lifecycle guide, cost optimization guide, Service Catalog guide, CONTRIBUTING.md
- Parameter validation added across all templates
- SageMaker Studio: Owner parameter made optional

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
