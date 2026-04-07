# Research Lifecycle Guide

Map your research phase to appropriate AWS templates.

## Phase 1: Planning & Proposal

**Activities:** Grant writing, cost estimation, architecture planning

**Templates:** None yet - use cost estimation guide

## Phase 2A: Data Collection

**Activities:** Data ingress, initial storage setup

**Recommended Templates:**
- `s3-research-bucket.yaml` - Store incoming data
- `ec2-general-purpose.yaml` - Data ingress processing
- `research-vpc.yaml` - If setting up shared infrastructure

## Phase 2B: Exploration & Development

**Activities:** Rapid iteration, experimentation, model development

**Recommended Templates:**
- `sagemaker-studio.yaml` - ML development
- `ec2-accelerated-gpu.yaml` - GPU experimentation
- `efs-shared-storage.yaml` - Shared datasets
- `s3-research-bucket.yaml` - Analysis results

**Cost Optimization:** Use Spot instances, smaller instance types

## Phase 2C: Production Computation

**Activities:** Large-scale computation, production runs

**Recommended Templates:**
- `parallelcluster-hpc.yaml` - HPC workloads
- `ec2-compute-optimized.yaml` - Batch processing
- `ec2-memory-optimized.yaml` - Memory-intensive analysis

**Cost Optimization:** Reserved instances for predictable workloads

## Phase 3: Archival & Publication

**Activities:** Long-term data storage, data sharing

**Recommended Templates:**
- `s3-research-bucket.yaml` - Automatic tiering to Glacier
- Keep minimal compute for data access

**Cost Optimization:** Lifecycle policies to Glacier Deep Archive

## Decision Matrix

| Need | Template |
|------|----------|
| Object storage | s3-research-bucket.yaml |
| Shared file system | efs-shared-storage.yaml |
| High-throughput storage | fsx-lustre.yaml |
| General computing | ec2-general-purpose.yaml |
| ML development | sagemaker-studio.yaml |
| GPU workloads | ec2-accelerated-gpu.yaml |
| HPC cluster | parallelcluster-hpc.yaml |
| Shared VPC | research-vpc.yaml |
| Budget tracking | budget-alert.yaml |
