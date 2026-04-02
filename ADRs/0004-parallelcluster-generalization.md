# ADR 0004: ParallelCluster Template Generalization

## Metadata
- **Status:** accepted
- **Date:** 2026-03-26
- **Subsystem:** templates/compute
- **Related:** ADR-0002 (security hardening), ADR-0003 (multi-queue design, proposed)

## Context

After the security hardening pass (ADR-0002), the ParallelCluster template needed generalization beyond the original MIT-specific use case. Several design decisions were MIT-specific: mandatory DCV, mandatory SSH key pair, mandatory software stack, no GPU/P-series support, hardcoded OS options including EOL Amazon Linux 2.

## Decisions

### DCV Remote Desktop Made Optional
Added `EnableDCV` parameter (yes/no, default yes). When disabled, the DCV config block, password secret, and DCV-related bootstrap steps are skipped. Researchers who only need CLI/Slurm access don't pay for desktop overhead.

### SSH Key Pair Made Optional
`KeyPairName` is now optional (default empty). ParallelCluster v3 doesn't require it. When blank, users connect via Session Manager (already configured via `AmazonSSMManagedInstanceCore` policy) or DCV. Session Manager is more secure (no key management, IAM-authenticated, audited via CloudTrail). SSH remains available for researchers who prefer it.

### DCV Password Moved to Secrets Manager
Replaced the S3-based password storage (ADR-0002) with AWS Secrets Manager. Purpose-built for secrets, provides encryption, CloudTrail audit trail, and rotation capability. Cost is negligible ($0.40/month). The bootstrap script retrieves the password via `aws secretsmanager get-secret-value` using the head node's IAM role. The password is permanent until changed manually via `passwd` on the head node.

### Software Stack Made Optional
Added `EnableSoftwareStack` parameter (yes/no, default yes). When yes, installs dev tools (emacs, git, gcc, python). When no, minimal cluster — for institutions using custom AMIs or who prefer manual setup. The bootstrap script always runs but checks the flag before installing.

### OS Options Trimmed
Removed `alinux2` (EOL June 2025), `rhel8`, `rhel9`. Kept `alinux2023` (default), `ubuntu2204`, `ubuntu2404`. RHEL/Rocky require custom AMIs and add licensing cost — advanced users can customize.

### Instance Type Constraints
- Head node: M-series and C-series only. Removed Hpc-series (designed for tightly-coupled compute with EFA, not suitable for Slurm controller/DCV workloads; `hpc6id` explicitly unsupported by ParallelCluster as head node).
- Compute: Added P-series (p4/p5/p6) for ML training alongside existing C/M/R/G/Hpc. P-series requires Capacity Block reservation.

### Capacity Block Support
Added `CapacityBlockId` parameter (optional). When provided, compute queue uses `CapacityType: CAPACITY_BLOCK` with the reservation ID. Required for P-series instances which cannot be launched on-demand. Users obtain the reservation separately via console/CLI.

### Subnet Descriptions Clarified
Updated descriptions to explain public vs private subnets in researcher-friendly language, since the target users may not know networking terminology.

### Session Manager Output Added
Added `SessionManagerCommand` output with the `aws ssm start-session` command. This is the primary access method when no SSH key is provided.

## Alternatives Considered

### Conditional Bootstrap Resources
Considered making the S3 bucket, Lambda, and upload custom resource conditional (only created when DCV or software stack is enabled). Rejected because CloudFormation `DependsOn` doesn't support `!If`, and the cluster resource references the bucket in multiple conditional blocks. Always creating these resources (they cost nothing when idle) avoids complex conditional dependency chains.

### SSM Parameter Store for DCV Password
Considered SSM SecureString instead of Secrets Manager. Rejected — Secrets Manager is the purpose-built service for application secrets, has better audit integration, and the cost difference is negligible.

## Consequences

### Positive
- Template works for CLI-only HPC users (no DCV), GUI researchers (DCV), and custom AMI institutions (no software stack)
- P-series GPU instances now supported via capacity blocks
- Session Manager as default access method is more secure than SSH keys
- Cleaner OS options (no EOL systems)

### Negative
- Always-created bootstrap resources (S3 bucket, Lambda) exist even when both DCV and software stack are disabled — minor resource overhead, zero cost
- Secrets Manager adds $0.40/month per cluster when DCV is enabled
- More parameters for users to consider (mitigated by sensible defaults and clear descriptions)
