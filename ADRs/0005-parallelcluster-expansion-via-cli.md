# ADR 0005: ParallelCluster Expansion via CLI, Not Template

## Metadata
- **Status:** accepted
- **Date:** 2026-03-27
- **Subsystem:** templates/compute
- **Supersedes:** ADR-0003 (multi-queue login nodes — now superseded)
- **Related:** ADR-0002, ADR-0004

## Context

ADR-0003 proposed adding optional GPU queues, login nodes, and capacity block support as parameterized features within the CloudFormation template. After further analysis, parameterizing variable-length Slurm queues, AD integration, and login nodes in CloudFormation fights the tool — CloudFormation parameters don't support dynamic lists, and the resulting template would be bloated with conditions for every combination.

Meanwhile, ParallelCluster's own CLI (`pcluster update-cluster`) is purpose-built for exactly this: adding queues, enabling login nodes, and configuring directory services on a running cluster without recreation.

## Decision

### Template scope: single compute queue, no login nodes, no AD
The CloudFormation template deploys a working cluster with one compute queue. This is the governed baseline that Service Catalog provisions. The template does not attempt to parameterize multiple queues, login nodes, or directory service integration.

### Post-deploy expansion via `pcluster update-cluster`
Admins expand clusters after deployment using the ParallelCluster CLI. We provide documented config snippets for common expansion patterns:

- **Adding a GPU queue** — second SlurmQueue with G/P-series instances
- **Adding a high-memory queue** — R-series instances for genomics/large datasets
- **Enabling login nodes** — LoginNodes section with instance type, count, subnet
- **Enabling AD/LDAP integration** — DirectoryService section with domain, endpoint, bind credentials
- **Adding FSx for Lustre** — for workloads that outgrow EFS throughput

### Documentation location
Config snippets and instructions go in `docs/` (e.g., `docs/parallelcluster-customization-guide.md`). Not in the template, not in steering docs — these are user-facing operational guides.

### Capacity blocks remain in the template
The `CapacityBlockId` parameter stays in the template (added in ADR-0004) because it must be set at queue creation time — it can't be added post-deploy to an existing queue. Users who need P-series instances provide the reservation ID at deploy time.

## Alternatives Considered

### Parameterized multi-queue in template (ADR-0003 approach)
Rejected. Pre-defining 2-3 optional queue slots with enable flags adds ~8 parameters and complex conditions for a feature that `pcluster update-cluster` handles natively. The template becomes harder to maintain and test for marginal UX gain — admins who need multiple queues are comfortable with CLI.

### Nested stacks per queue
Rejected (same reasoning as ADR-0003). ParallelCluster cluster config is a single atomic resource.

### Separate templates for different cluster profiles
Rejected. Creates maintenance burden (N templates to keep in sync) and doesn't solve the "add a queue later" problem.

## Consequences

### Positive
- Template stays focused and maintainable (~720 lines, 17 parameters)
- Service Catalog product is simple to provision
- No artificial limits on queue count, instance types, or user count
- Expansion uses ParallelCluster's native tooling (validated, documented by AWS)
- Testing matrix stays manageable (one queue configuration)

### Negative
- Adding queues/users requires CLI knowledge (mitigated by documentation with copy-paste snippets)
- Post-deploy changes aren't tracked in CloudFormation state (ParallelCluster manages its own state)
- Institutions need ParallelCluster CLI installed for expansion (not just for initial deploy)
