# ADR 0002: ParallelCluster Template Security Hardening and Research Cloud Toolkit Alignment

## Metadata
- **Status:** accepted
- **Date:** 2026-03-26
- **Subsystem:** templates/compute
- **Related:** ADR-0001 (service catalog simplification), parallelcluster-deployment steering doc

## Context

The ParallelCluster HPC template (`templates/compute/parallelcluster-hpc.yaml`) was originally developed for a specific MIT use case. Before generalizing it for broader institutional use, it needed a security review and alignment with Research Cloud Toolkit conventions established in Phase 1 (EC2, S3, EFS templates).

Key issues identified:
- DCV password passed as a shell argument to the bootstrap script (visible in `/proc`, ParallelCluster logs, CloudFormation events)
- DCV remote desktop open to `0.0.0.0/0` by default
- Missing standard Research Cloud Toolkit cost-tracking tags (Project, CostCenter, Owner, ManagedBy, Environment)
- Lambda IAM policies using `Resource: '*'` where narrower scoping was feasible
- Bootstrap script had inconsistent indentation in the DCV configuration section
- Lambda delete handler used bare `except: pass` (swallowed errors silently)
- Unused CloudFormation conditions and redundant `DependsOn`
- Hardcoded `arn:aws:iam::` instead of partition-aware `arn:${AWS::Partition}:iam::`

## Decision

### DCV Password Handling
Store the DCV password as a separate encrypted file in the bootstrap S3 bucket (`.dcv-password`) instead of passing it as a script argument. The bootstrap script reads it from S3 using the head node's IAM role (which already has S3 read access to the bucket). The Lambda that uploads the bootstrap script now also uploads the password file with SSE-AES256 encryption.

### DCV Network Access
Replace hardcoded `AllowedIps: '0.0.0.0/0'` with a required `DCVAllowedIps` parameter (CIDR format, no default). Forces deployers to explicitly choose their access scope.

### Tag Alignment
Added `ProjectName`, `CostCenter`, and `Owner` parameters matching the EC2 template pattern. All taggable resources now carry the 5 standard Research Cloud Toolkit tags (Project, CostCenter, Owner, ManagedBy, Environment). Owner is optional with conditional inclusion.

### IAM Scoping
- EIP association Lambda: split `ec2:AssociateAddress`/`ec2:DisassociateAddress` (scoped to account/region) from `ec2:Describe*` actions (require `Resource: '*'` per AWS API design)
- All managed policy ARNs use `${AWS::Partition}` for GovCloud/China partition compatibility

### Bootstrap Script Cleanup
- Fixed indentation (DCV config section was indented under a comment block)
- Replaced echo-per-line systemd service creation with heredoc (`cat > file << EOF`)
- Lambda delete handler now logs errors instead of silently swallowing them

### Template Hygiene
- Removed unused conditions (`UseSpotInstances`, `IsAmazonLinux`, `IsRHEL`)
- Removed redundant `DependsOn: PclusterCluster` on EIPAssociation (already implied by `GetAtt`)
- EIP association Lambda timeout reduced from 900s to 500s (operation completes in 2-3 min)

## Alternatives Considered

### SSM SecureString for DCV password
Considered storing the password in SSM Parameter Store (SecureString) and reading it from the bootstrap script. Rejected because it would require adding SSM permissions to the ParallelCluster head node role (which is managed by ParallelCluster, not our template) and adds a resource dependency. The S3 approach uses infrastructure the template already creates and the head node already has access to.

### Secrets Manager for DCV password
Same issue as SSM — requires additional IAM permissions on the ParallelCluster-managed head node role. Over-engineered for a single password value.

### Default CIDR for DCVAllowedIps
Considered defaulting to `0.0.0.0/0` for ease of use. Rejected because a permissive default undermines the security intent. Forcing an explicit choice is a small friction that prevents accidental exposure.

## Consequences

### Positive
- DCV password no longer visible in process listings, logs, or CloudFormation events
- All resources tagged consistently for cost tracking across the Research Cloud Toolkit portfolio
- IAM follows least-privilege more closely
- cfn-lint passes clean (zero warnings)
- Template is partition-aware (works in GovCloud/China)

### Negative
- Deployers must now provide 3 additional parameters (ProjectName, CostCenter, DCVAllowedIps) — minor friction, but consistent with all other Research Cloud Toolkit templates
- Bootstrap script now depends on AWS CLI being available on the head node to read from S3 (it is — ParallelCluster pre-installs it)
- Existing MIT deployments will need to add the new required parameters on stack update
