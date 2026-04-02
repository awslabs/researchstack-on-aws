---
status: accepted
date: 2026-03-27
subsystem: storage/efs, compute/ec2, compute/parallelcluster
related: []
---

# 0005 - EFS Security Group Uses VPC CIDR Instead of Security Group Chaining

## Context

The EFS template (`efs-shared-storage.yaml`) needs to allow NFS access (port 2049) from compute resources that mount the filesystem. These consumers include EC2 instances, ParallelCluster head/compute nodes, SageMaker, and potentially ECS or Lambda.

The original design used a self-referencing security group: the EFS mount targets had a security group that only allowed NFS from instances with that same security group attached. Consumers (EC2 templates) accepted an `EfsSecurityGroupId` parameter and attached it to their instances.

This broke with ParallelCluster because ParallelCluster manages its own security groups and doesn't support injecting additional security groups into its head/compute node configuration via the EFS settings block.

## Decision

Replace the self-referencing security group ingress rule with a VPC CIDR-based ingress rule. Any instance in the VPC can mount the EFS filesystem over NFS. The VPC CIDR is derived automatically from the VPC ID parameter using a Lambda-backed custom resource (CloudFormation doesn't support `GetAtt` on VPC IDs passed as parameters).

Consequently, the `EfsSecurityGroupId` parameter was removed from all four EC2 templates. Consumers now only need the `EfsFileSystemId` to mount.

## Alternatives Considered

1. **Self-referencing security group (original)**: More precise access control, but requires every consumer to know about and attach the EFS security group. Doesn't work with ParallelCluster or any service that manages its own security groups.

2. **Optional additional CIDR/SG parameter on EFS template**: Adds complexity for the user. Researchers would need to understand security group chaining.

3. **VPC CIDR ingress (chosen)**: Any instance in the VPC can mount. Simpler for all consumers. Works with ParallelCluster, SageMaker, ECS, and any future compute template without modification.

## Consequences

- **Broader access**: Any instance in the VPC can reach the EFS on port 2049. In a shared VPC with multiple teams, this means cross-team NFS access is possible. The toolkit's model assumes one VPC per research group/project, so the VPC is the trust boundary.
- **TLS enforcement**: The EFS filesystem policy still enforces TLS (`aws:SecureTransport`), so connections are encrypted in transit regardless of the security group rule.
- **Simpler consumer templates**: EC2 templates dropped from 1 parameter to 0 for EFS connectivity. ParallelCluster works without any special configuration.
- **Lambda dependency**: The VPC CIDR lookup adds a Lambda function, IAM role, and custom resource to the EFS stack. These are lightweight (runs once at create, ~30s) but add resources to the stack.
