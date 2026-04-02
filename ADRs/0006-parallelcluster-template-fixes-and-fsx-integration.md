---
status: accepted
date: 2026-03-30
subsystem: compute/parallelcluster, storage/fsx-lustre, storage/efs
related: [0005-efs-vpc-cidr-security-group]
---

# 0006 - ParallelCluster Template Fixes and FSx Lustre Integration

## Context

Integration testing of the ParallelCluster HPC template (`parallelcluster-hpc.yaml`) against a live AWS account revealed multiple issues across template deployment, IAM permissions, storage interoperability, and Lustre client compatibility. This ADR documents all fixes applied during the testing cycle.

## Decisions

### 1. CloudFormation Capabilities

CLI deployment requires all three capabilities: `CAPABILITY_IAM`, `CAPABILITY_NAMED_IAM`, and `CAPABILITY_AUTO_EXPAND`. The ParallelCluster provider is a nested stack (`AWS::CloudFormation::Stack`) that itself nests a policies stack with named IAM resources.

### 2. Scoped DCV Secrets Manager Policy

Replaced the `SecretsManagerReadWrite` AWS managed policy with a custom managed policy (`DCVSecretsPolicy`) scoped to only the DCV password secret. The policy is named with a `parallelcluster` prefix so the ParallelCluster Lambda's IAM admin policy allows attaching it (the provider allowlists `arn:...:policy/parallelcluster*`).

This was required because the ParallelCluster provider's `DefaultParallelClusterIamAdminPolicy` has a condition on `iam:AttachRolePolicy` that only allows a specific set of AWS managed policies. `SecretsManagerReadWrite` was not in that allowlist.

Bonus: this is better security — the head node can only read the specific DCV password secret, not all secrets in the account.

### 3. EFS Encryption in Transit

Added `EncryptionInTransit: true` to the existing EFS mount configuration in the ParallelCluster template. This is required when mounting EFS filesystems deployed by our `efs-shared-storage.yaml` template, which enforces TLS via a filesystem policy (`aws:SecureTransport` deny rule). Without this, ParallelCluster mounts EFS without TLS and the connection is rejected.

### 4. FSx Lustre Template — PERSISTENT_2 Default

The FSx Lustre template (`fsx-lustre.yaml`) defaults to `PERSISTENT_2` for all deployments. `SCRATCH_2` runs Lustre server version 2.10.x, which is incompatible with the 2.15.x Lustre client on Amazon Linux 2023 and recent Ubuntu AMIs. The mount fails with `EINVAL` (exit code 22) and the error: "Server MGS version (2.10.5.0) refused connection from this client with an incompatible version (2.15.6)."

PERSISTENT_2 runs a compatible Lustre server version. The cost difference is negligible (~$0.005/GB/month), and PERSISTENT_2 provides data replication that SCRATCH_2 lacks.

### 5. FSx Lustre Template — Simplified Parameters

Reduced from 10 parameters to 7 by removing `DeploymentType`, `PerUnitStorageThroughput`, `S3ImportPrefix`, and `AutoImportPolicy`. Deployment type is always PERSISTENT_2, throughput defaults to 125 MB/s/TiB, S3 imports the entire bucket, and auto-sync is full bidirectional (NEW/CHANGED/DELETED).

### 6. FSx Lustre Security Group — Self-Referencing Rules

Added self-referencing security group rules for Lustre ports (988, 1021-1023) in addition to the VPC CIDR rules. Required for Lustre internal communication between filesystem ENIs.

### 7. FSx Lustre S3 Data Repository Associations

S3 linking requires PERSISTENT_2 (DRAs are not supported on SCRATCH_2). The template auto-selects PERSISTENT_2 when S3 is provided. Auto-import/export events use FSx enum values (`NEW`, `CHANGED`, `DELETED`), not S3 event names.

## Testing Summary

| Test | Configuration | Result |
|------|--------------|--------|
| 1 - Baseline | alinux2023, On-Demand, no DCV | ✅ |
| 2 - DCV | alinux2023, DCV enabled | ✅ |
| 3 - Graviton | ubuntu2204, m7g/c7g, DCV | ✅ |
| 4 - Storage | Existing EFS + S3 + SSH key | ✅ |
| 5 - Spot + EFS | Spot pricing, EFS from template (TLS) | ✅ |
| 6 - Lustre | PERSISTENT_2 FSx with S3, PCluster mount | ✅ |
| EC2 templates (4) | EFS mount without SG parameter | ✅ |
| EFS template | VPC CIDR lookup, NFS ingress | ✅ |
| FSx standalone | SCRATCH_2 (no PCluster) | ✅ |
| FSx + S3 | PERSISTENT_2 with DRA | ✅ |

## Consequences

- ParallelCluster CLI deployment requires documenting all three capabilities
- DCV-enabled clusters use a scoped IAM policy instead of a broad AWS managed policy
- Existing EFS filesystems with TLS enforcement work out of the box with ParallelCluster
- FSx Lustre always deploys as PERSISTENT_2, which costs marginally more than SCRATCH_2 but is compatible with current AMIs
- SCRATCH_2 support can be re-added when AWS updates the Lustre server version or when client compatibility is resolved
