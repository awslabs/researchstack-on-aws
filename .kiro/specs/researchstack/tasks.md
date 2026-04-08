# ResearchStack on AWS - Implementation Tasks

## Phase 1: Repository Structure + Initial Templates (COMPLETE)

### 1. Repository Restructuring
- [x] 1.1 Create new repository structure with templates-first organization
- [x] 1.2 Copy existing templates from cfn-templates folder
- [x] 1.3 Organize templates by category (compute, storage, ml, networking)
- [x] 1.4 Keep templates flat (no per-template subdirectories or READMEs)
- [x] 1.5 Update main README with new structure and usage

### 2. Template Standardization (for existing templates)
- [x] 2.1 Define template metadata schema (ResearchLifecycle, QuickSuite)
- [x] 2.2 Add required cost tracking tags to all templates (Project, CostCenter, Owner, ManagedBy, Environment)
- [x] 2.3 Ensure security defaults (encryption, public access blocking)
- [x] 2.4 Add parameter validation and helpful defaults
- [x] 2.5 Convert JSON templates to YAML for consistency
- [ ]* 2.6 Create template validation script (deferred - only needed for community contributions)

### 3. Initial Documentation
- [x] 3.1 Create research lifecycle mapping guide (basic version)
- [x] 3.2 Write cost estimation guide with F&A considerations (basic version)
- [x] 3.3 Create deployment guide for standalone CloudFormation usage
- [x] 3.4 Document template standards in CONTRIBUTING.md

### 4. Initial Templates (based on existing cfn-templates)
- [x] 4.1 S3 research bucket (adapt s3-bucket.yaml)
- [x] 4.2 SageMaker Studio (adapt sagemaker-studio-domain.yaml)
- [x] 4.3 EFS shared storage (adapt efs-service-catalog.yaml)
- [x] 4.4 EC2 instances - split by category:
  - [x] 4.4.1 General purpose (m-series)
  - [x] 4.4.2 Memory optimized (r-series)
  - [x] 4.4.3 Compute optimized (c-series)
  - [x] 4.4.4 GPU/Accelerated instances (g/p-series, Trainium, Inferentia)
  - [x] 4.4.5 HPC optimized (hpc-series)
- [x] 4.5 ParallelCluster (adapt parallelcluster-full.yaml)
- [x] 4.6 Research VPC (networking folder)


## Phase 2: Service Catalog (Simplified CDK) — per ADR 0001

### 5. CDK Scaffolding
- [x] 5.1 Create `researchstack/service-catalog/` directory with cdk.json, pyproject.toml
- [x] 5.2 Create simplified framework_config.yaml (no modules system, no hub_vpc section)
- [x] 5.3 Create example portfolio TOML config with inline product definitions pointing at ../templates/

### 6. Port Core Code (simplified from SCAR)
- [x] 6.1 Port app.py — simplified entrypoint (no optional modules, no config_validator, standard logging)
- [x] 6.2 Port framework_config.py — drop ModuleConfig, HubVpcConfig, PermissionSetConfig; keep deployment + tagging
- [x] 6.3 Port portfolio_config.py — inline product definitions (name, template path, launch_role_policies), drop personas
- [x] 6.4 Port base_portfolio.py (PortfolioStack) — drop service actions, drop persona config, keep portfolio creation + OU sharing + product deployment
- [x] 6.5 Port assets_stack.py (renamed from shared_resources_stack.py) — S3 bucket for SC template artifacts

### 7. Port Constructs (simplified from SCAR)
- [x] 7.1 Port stackset_factory.py — drop service action stackset support, keep launch role stacksets only
- [x] 7.2 Port launch_role_construct.py — drop Hub VPC SSM policy, keep per-product IAM roles
- [x] 7.3 Port launch_role_stackset_template.py + base_stackset_template.py
- [x] 7.4 Port portfolio_share.py — keep as-is (OU sharing via custom resource)

### 8. Port Utils (simplified from SCAR)
- [x] 8.1 Port config.py — GlobalConfig singleton (project_slug, env_name)
- [x] 8.2 Port resource_naming.py — drop Hub VPC references, keep stack/role naming + validators
- [x] 8.3 Port tagging.py — keep as-is

### 9. Documentation & Cleanup
- [x] 9.1 Update researchstack/README.md with actual repo structure
- [x] 9.2 Add SC deployment instructions to README or docs/
- [x] 9.3 Accept ADR 0001 (proposed → accepted)

### 10. Near-Term Follow-ups
- [ ] 10.1 Create architecture diagram (hub account, StackSets, OU sharing, launch roles)
- [x] 10.2 Automate IDC portfolio access assignment (replace manual console steps)
- [ ] 10.3 Test `cdk synth` and `cdk deploy` against a real AWS account
- [ ] 10.3.1 Verify ParallelCluster launch role policies are sufficient; scope down IAMFullAccess to least privilege if possible
- [ ] 10.3.2 Scope down IAMFullAccess on EC2 launch roles to a custom managed policy with only the IAM actions needed (CreateRole, DeleteRole, PutRolePolicy, CreateInstanceProfile, PassRole, etc.) — single reusable policy across all EC2 products
- [ ] 10.4 Automate Service Catalog TagOptions (enforce cost tracking tags at provisioning time)
- [ ] 10.4.1 Design centralized tag config that feeds both SC TagOptions and IDC ABAC attribute mappings — needs to handle deduplication with template parameters and institution-specific ABAC tag keys
- [ ] 10.4.2 Add optional S3 bucket ABAC enablement (`PutBucketAbac`) to S3 template — allows tag-based IAM conditions to be enforced on the bucket (see https://docs.aws.amazon.com/AmazonS3/latest/userguide/buckets-tagging-enable-abac.html)
- [x] 10.5 Document `share_tag_options` and `share_principals` in portfolio TOML config once TagOptions and IDC access automation are implemented
- [ ] 10.6 Create `docs/cloud-concepts-for-researchers.md` — lightweight glossary covering VPC, subnets, security groups, AZs/regions, NAT gateway, storage types (S3 vs EFS vs EBS), instance families, and how Service Catalog abstracts it all. Target audience: PIs and IT admins at small institutions who want to understand what they're deploying.
- [ ] 10.6.1 Include SSM Session Manager usage guide (how to connect, plugin install, no SSH keys needed), AMI selection guidance (architecture must match instance type family), default OS users (ssm-user for SSM sessions, ec2-user for AL2023, ubuntu for Ubuntu), and note that POSIX user management is outside ResearchStack scope.
- [ ] 10.6.2 Document custom AMI support: institutions can store custom AMIs in SSM at a convention path (e.g., `/arc/ami/{name}`), then add that path to the `AllowedValues` list in the EC2 template. SSM value can be updated anytime without redeploying the template — only the initial path addition requires a template update.
- [ ] 10.7 Spot instance support — either as a toggle in existing EC2 templates or as separate spot-specific products. Key for cost-sensitive research workloads (fault-tolerant batch jobs, training runs with checkpointing).
- [ ] 10.8 NICE DCV-enabled instances — interactive remote desktop for visualization, pre/post-processing, GUI-based tools. Likely a separate template with DCV licensing, security group rules (TCP 8443), and session management.
- [ ] 10.9 Capacity Blocks for GPU instances — required for on-demand P-series access (p5, p4d, etc.) since these are generally unavailable without reservations. Spot is the alternative path for GPU if capacity blocks aren't feasible. Evaluate which approach (or both) to offer.
- [ ] 10.10 ~~Evaluate Mountpoint for Amazon S3~~ → **Evaluate Amazon S3 Files** (launched April 2026) — S3 Files provides full POSIX filesystem access to S3 buckets via NFS (built on EFS), with read/write support, sub-millisecond latency for active data, and automatic sync back to S3. Supersedes Mountpoint for most use cases. Could replace EFS for shared storage in many research workloads at ~13x lower storage cost. Evaluate: (1) add optional `S3FilesFileSystemId` parameter to EC2 templates, (2) new storage template to create S3 Files filesystem on an existing bucket, (3) ParallelCluster support status, (4) update cost optimization guide with EFS vs S3 Files comparison. Wait for service to stabilize before building templates.
- [ ] 10.11 Evaluate existing templates (Transfer Family web app, PCS, etc.) for inclusion in ResearchStack — review scope, fit, and whether they should be added as-is, adapted, or kept separate.
- [ ] 10.12 Revisit standalone HPC EC2 product — removed in Phase 2 because single HPC instances without placement groups/EFA aren't useful (ParallelCluster covers multi-node, C/R covers single-node). Revisit if there's demand for a single-node HPC template with placement group + EFA baked in.
- [ ] 10.13 Create Neuron accelerator template (Trainium/Inferentia) — separate from GPU template because Neuron SDK is a different software stack from CUDA (different drivers, AMIs, compilation paths). Would use trn1/trn2/inf2 instance types with Neuron DLAMIs. Evaluate demand before building.

## Phase 2B: Cost Governance — per ADR 0007

### 10A. Governance Budget Product (new template)
- [x] 10A.1 Create `templates/governance/` directory and `budget-alert.yaml` template with parameters
- [x] 10A.2 Implement core budget resources (SNS topic, email subscription, AWS Budget with CostCenter + optional Project tag filters)
- [x] 10A.3 Implement notification thresholds (50% actual, 80% actual, 100% forecasted)
- [x] 10A.4 Implement ENFORCE mode: IAM deny policy on target role blocking new EC2/SageMaker launches (auto-resets monthly). Note: account-wide EC2 stop not feasible via Budget Actions (requires instance IDs) — handled by EC2-embedded budget and idle shutdown instead.
- [x] 10A.5 Add tagging and outputs
- [x] 10A.6 Add budget-alert product to Service Catalog portfolio TOML
- [x] 10A.7 Update cost optimization guide and templates/README.md

### 10B. EC2-Embedded Budget (template enhancement)
- [ ] 10B.1 Add EnableInstanceBudget (no/notify/enforce), MonthlyInstanceBudgetUSD, BudgetNotificationEmail parameters + conditional budget resources to ec2-general-purpose.yaml
- [ ] 10B.2 Add enforce mode: conditional IAM role (scoped to instance ARN) + Budget Action to stop just this instance
- [ ] 10B.3 Repeat 10B.1-10B.2 for ec2-compute-optimized.yaml
- [ ] 10B.4 Repeat 10B.1-10B.2 for ec2-memory-optimized.yaml
- [ ] 10B.5 Repeat 10B.1-10B.2 for ec2-accelerated-gpu.yaml
- [ ] 10B.6 Verify EC2 launch role policies in portfolio TOML cover budgets:* (add if needed)

### 10C. EC2 Idle Instance Shutdown (template enhancement)
- [ ] 10C.1 Add EnableIdleShutdown + IdleMinutesBeforeShutdown parameters and CloudWatch alarm to ec2-general-purpose.yaml
- [ ] 10C.2 Repeat for ec2-compute-optimized.yaml
- [ ] 10C.3 Repeat for ec2-memory-optimized.yaml
- [ ] 10C.4 Repeat for ec2-accelerated-gpu.yaml
- [ ] 10C.5 Verify EC2 launch role policies cover cloudwatch:PutMetricAlarm and ec2:StopInstances

## Phase 3: Quick Suite Integration (1-2 months)

> **Note:** Templates originally carried `ResearchLifecycle` and `QuickSuite` metadata blocks (phase mappings, keywords, use cases). These were stripped during Phase 2 cleanup as dead weight, but Phase 3's GenAI layer will likely need similar metadata for template recommendation and phase-aware suggestions. Revisit what structured metadata the AI agent needs and define a schema then.

### 6. Quick Suite Setup
- [ ] 6.1 Create Quick Suite workspace
- [ ] 6.2 Set up Quick Index with template catalog
- [ ] 6.3 Upload research lifecycle guide to Quick Index
- [ ] 6.4 Configure AWS Pricing API integration
- [ ] 6.5 Test Quick Index search and retrieval
- [ ] 6.6 Update documentation for Quick Suite integration

### 7. Quick Research Agent
- [ ] 7.1 Define agent instructions and persona
- [ ] 7.2 Create phase-specific knowledge sources
- [ ] 7.3 Implement template recommendation logic
- [ ] 7.4 Add cost estimation with F&A calculations
- [ ] 7.5 Generate budget justification text
- [ ] 7.6 Test agent with sample research scenarios

### 8. Phase-Specific Spaces
- [ ] 8.1 Create "Phase 1 - Planning" space
- [ ] 8.2 Create "Phase 2A - Data Collection" space
- [ ] 8.3 Create "Phase 2B - Exploration" space
- [ ] 8.4 Create "Phase 2C - Production" space
- [ ] 8.5 Create "Phase 3 - Archival" space
- [ ] 8.6 Configure custom chat agents per space

### 9. Quick Flows for Deployment
- [ ] 9.1 Create "Deploy via Service Catalog" flow
- [ ] 9.2 Create "Deploy via CloudFormation" flow
- [ ] 9.3 Add parameter validation step
- [ ] 9.4 Add cost estimation step
- [ ] 9.5 Add deployment tracking
- [ ] 9.6 Test flows with sample deployments

### 10. Quick Automate Integration
- [ ] 10.1 Create Service Catalog API action
- [ ] 10.2 Create CloudFormation API action
- [ ] 10.3 Create AWS Pricing API action
- [ ] 10.4 Add error handling and retries
- [ ] 10.5 Implement deployment status tracking
- [ ] 10.6 Test automation workflows

## Phase 4: Community & Expansion (Ongoing)

### 11. Additional Templates (after Phase 2 learnings)
- [ ] 11.1 EC2 Spot instance variants (general-purpose, compute-optimized, memory-optimized, gpu)
- [ ] 11.2 RDS PostgreSQL (database)
- [ ] 11.3 Batch compute environment (parallel processing)
- [ ] 11.4 Athena workspace (data analytics)
- [ ] 11.5 Glacier vault (long-term archival)
- [ ] 11.6 Create compliance templates (HIPAA, FedRAMP)
- [ ] 11.7 Add multi-region templates
- [ ] 11.8 Create cost optimization templates
- [ ] 11.9 Add data pipeline templates
- [ ] 11.10 Create ML/AI templates (Bedrock, etc.)

### 12. Community Infrastructure
- [ ] 12.1 Create CONTRIBUTING.md with guidelines
- [ ] 12.2 Set up GitHub issue templates
- [ ] 12.3 Create PR template with checklist
- [ ] 12.4 Add automated template validation (GitHub Actions)
- [ ] 12.5 Set up automated testing
- [ ] 12.6 Create community discussion forum

### 13. Case Studies & Examples
- [ ] 13.1 Document MIT deployment case study
- [ ] 13.2 Create example for small institution
- [ ] 13.3 Create example for large institution
- [ ] 13.4 Document Quick Suite integration example
- [ ] 13.5 Create video tutorials
- [ ] 13.6 Write blog posts for AWS blog

### 14. Cost Management Module (Separate Repo)
- [ ] 14.1 Design cost tracking architecture
- [ ] 14.2 Create cost allocation dashboard
- [ ] 14.3 Implement budget alerts
- [ ] 14.4 Add chargeback reporting
- [ ] 14.5 Create cost optimization recommendations
- [ ] 14.6 Document cost management setup

## Maintenance Tasks (Ongoing)

### 15. Template Maintenance
- [ ] 15.1 Review and update templates quarterly
- [ ] 15.2 Update cost estimates with current pricing
- [ ] 15.3 Add new AWS services as they become available
- [ ] 15.4 Respond to community issues and PRs
- [ ] 15.5 Update documentation based on feedback
- [ ] 15.6 Monitor AWS service changes and deprecations

### 16. Service Catalog Maintenance
- [ ] 16.1 Update deploy.py script as needed
- [ ] 16.2 Monitor StackSet deployments
- [ ] 16.3 Update launch role permissions
- [ ] 16.4 Review and update portfolio configurations
- [ ] 16.5 Test with new AWS Organizations features
- [ ] 16.6 Update documentation for new features

### 17. Quick Suite Maintenance
- [ ] 17.1 Update agent instructions based on feedback
- [ ] 17.2 Refine knowledge sources
- [ ] 17.3 Improve cost estimation accuracy
- [ ] 17.4 Add new deployment workflows
- [ ] 17.5 Monitor Quick Suite updates and new features
- [ ] 17.6 Update integration code as APIs change
