# ADR 0003: ParallelCluster Multi-Queue, Login Nodes, and Capacity Blocks

## Metadata
- **Status:** superseded
- **Superseded by:** ADR-0005 (expansion via CLI)
- **Date:** 2026-03-26
- **Subsystem:** templates/compute
- **Related:** ADR-0002 (parallelcluster security hardening), parallelcluster-deployment steering doc

## Context

The current ParallelCluster template (`parallelcluster-hpc.yaml`) deploys a single Slurm compute queue. Real-world HPC usage at institutions typically requires:

1. **Multiple queues/partitions** — e.g., `cpu-compute` (C-series), `gpu-compute` (G-series), `high-mem` (R-series) so researchers can target the right hardware for their workload via `sbatch -p gpu-compute`.
2. **Login nodes** — ParallelCluster 3.7+ supports dedicated login nodes that offload user SSH sessions from the head node. Important for multi-user clusters where multiple researchers share the same cluster.
3. **Capacity blocks** — P-series GPU instances (p5, p6) cannot be launched on-demand. They require EC2 Capacity Block reservations. Without support, the template silently fails if someone picks a P-series compute type.

These are separate features but they interact: a GPU queue might need capacity blocks, and login nodes become more valuable as user count grows.

## Decision

### Approach: Parameterized Multi-Queue in a Single Template

Keep the single CloudFormation template (Service Catalog compatible) but add optional queues and login nodes via parameters and conditions.

**Why not nested stacks:** The ParallelCluster custom resource takes a single `ClusterConfiguration` YAML blob — the cluster is one atomic resource. Nested stacks can't split the cluster config across stacks. They'd only separate supporting infrastructure (S3 bucket, Lambdas) from the cluster, which doesn't justify the added complexity.

### Proposed Parameter Design

```yaml
# Primary compute queue (required, exists today)
ComputeInstanceType: c7i.8xlarge
ComputePricingModel: ONDEMAND
MaxComputeNodes: 10

# GPU queue (optional)
EnableGPUQueue: 'no'          # yes/no
GPUInstanceType: g6.12xlarge
GPUPricingModel: ONDEMAND
MaxGPUNodes: 4

# Capacity block (optional, for P-series GPU queue)
CapacityBlockId: ''           # CB reservation ID, blank = not used

# Login nodes (optional)
EnableLoginNodes: 'no'        # yes/no
LoginNodeInstanceType: m7i.xlarge
LoginNodeCount: 1
LoginNodeSubnetId: ''         # can reuse head node subnet
```

### Cluster Configuration Mapping

The template uses CloudFormation conditions to build the `ClusterConfiguration`:
- Primary queue always present under `SlurmQueues`
- GPU queue added conditionally as a second entry in `SlurmQueues`
- If `CapacityBlockId` is provided, GPU queue uses `CapacityType: CAPACITY_BLOCK` with the reservation ID
- Login nodes section added conditionally under `LoginNodes`

### Login Nodes Design

- Login nodes inherit the head node's `AllowedIps` for SSH
- DCV runs on login nodes (not head node) when login nodes are enabled — this is the recommended pattern for multi-user clusters
- Bootstrap script runs on login nodes via `CustomActions` (same software stack as head node)
- Login nodes share the same EFS `/shared` storage as the rest of the cluster

### Capacity Blocks Design

- Only applicable to the GPU queue (P-series instances)
- User must obtain a Capacity Block reservation separately (console/CLI) and provide the ID
- Template validates: if `CapacityBlockId` is provided, `EnableGPUQueue` must be `yes`
- `CapacityType` set to `CAPACITY_BLOCK` instead of `ONDEMAND`/`SPOT`

## Alternatives Considered

### 1. Separate templates per queue configuration
Rejected. Would create a combinatorial explosion of templates (cpu-only, cpu+gpu, cpu+gpu+login, etc.) and break the single-product Service Catalog model.

### 2. Nested stacks
Rejected. ParallelCluster cluster config is a single atomic resource — can't be split across stacks. Nested stacks would only separate Lambdas/S3 from the cluster, adding complexity without meaningful benefit.

### 3. Post-deploy `pcluster update-cluster` for adding queues
Considered. Users could deploy the base cluster and add queues via CLI. This works but defeats the "one-click Service Catalog" goal and requires CLI knowledge. Better to parameterize upfront.

### 4. Full flexibility via JSON/YAML parameter for arbitrary queue configs
Rejected. CloudFormation parameters don't support complex nested structures well. Would require a Lambda to parse and validate, adding fragility. The parameterized approach covers 90% of use cases with much less complexity.

## Consequences

### Positive
- Researchers can target CPU vs GPU hardware via Slurm partitions without deploying separate clusters
- Login nodes enable multi-user access without overloading the head node
- Capacity blocks unlock P-series GPU instances that are otherwise inaccessible
- Single template remains Service Catalog compatible

### Negative
- Parameter count increases significantly (~6-8 new parameters)
- CloudFormation conditions become more complex (nested conditionals for queue building)
- Testing matrix grows: need to validate base, base+GPU, base+GPU+CB, base+login, all combinations
- Login node bootstrap adds deployment time

### Implementation Estimate
- Multi-queue (CPU + optional GPU): moderate — mainly parameter/condition work in the existing template
- Capacity blocks: small — one additional parameter and a condition on `CapacityType`
- Login nodes: larger — new config section, bootstrap script changes, DCV routing decision
- Recommended order: GPU queue → capacity blocks → login nodes

## Open Questions
1. Should DCV move entirely to login nodes when enabled, or remain on head node as well?
2. Should we support more than one optional queue (e.g., GPU + high-mem), or is two queues (primary + GPU) sufficient for v1?
3. For capacity blocks, should the template validate that the instance type matches the reservation, or let ParallelCluster handle the error?
