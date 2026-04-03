# ParallelCluster HPC Guide

Deploy and operate a Slurm HPC cluster on AWS using the Research Cloud Toolkit's ParallelCluster template.

## What the Template Provides

The template deploys a production-ready HPC cluster with one CloudFormation stack:

- **Slurm scheduler** with one auto-scaling compute queue (nodes launch on job submission, terminate when idle)
- **Shared EFS storage** at `/shared` (auto-created or bring your own)
- **Optional DCV remote desktop** for GUI access via web browser
- **Elastic IP** so the head node IP address never changes across stop/start cycles
- **Session Manager access** (no SSH keys required)
- **Cost tracking tags** on all resources (Project, CostCenter, Owner)

After deployment, you can expand the cluster with additional compute queues, multi-user access via Active Directory, login nodes, and more — see [Post-Deploy Customization](#post-deploy-customization).

## Quick Start

### 1. Prerequisites

- A VPC with a public subnet (head node) and a private subnet with NAT Gateway (compute nodes). Deploy the `research-vpc.yaml` template first if you don't have one.
- An EC2 key pair — only if you want SSH access. [Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html) and [DCV remote desktop](https://docs.aws.amazon.com/dcv/latest/userguide/what-is-dcv.html) work without one. Session Manager lets you connect to instances through the AWS CLI or console without opening inbound ports or managing SSH keys. DCV provides a full GUI desktop accessible via web browser.

### 2. Deploy

Deploy via the CloudFormation console, CLI, or Service Catalog.

**Required parameters:**

| Parameter | What to enter |
|-----------|---------------|
| ProjectName | Your research project name (e.g., `genomics-lab`) |
| CostCenter | Department or grant number for billing |
| HeadNodeSubnetId | A public subnet (one with a route to an internet gateway) |
| ComputeSubnetId | A private subnet with NAT Gateway (in the same VPC). If unsure, use the same public subnet as the head node — it works, but a private subnet is more secure. |

**DCV parameters (when EnableDCV = yes):**

| Parameter | What to enter |
|-----------|---------------|
| DCVAllowedIps | Your office/campus CIDR (e.g., `203.0.113.0/24`). Use `0.0.0.0/0` to allow access from anywhere. |
| DCVPassword | Password for the DCV desktop login. Min 8 characters. |

**Optional configuration — safe to leave as defaults:**

| Parameter | Default | When to change |
|-----------|---------|----------------|
| ClusterName | research-cluster | When running multiple clusters in the same account |
| OperatingSystem | alinux2023 | Ubuntu 22.04/24.04 if your software requires it |
| HeadNodeInstanceType | m7i.2xlarge | Larger if running DCV with heavy GUI apps, smaller if CLI-only |
| ComputeInstanceType | c7i.8xlarge | Match to your workload: R-series for memory, G-series for GPU, Hpc-series for tightly-coupled MPI. See the [EC2 Instance Type Explorer](https://aws.amazon.com/ec2/instance-explorer/) for family overviews, or [Vantage](https://instances.vantage.sh/?id=421e512ec7fc071920ffc00ca2bc7141ef1c98aa) to compare specs and pricing side-by-side. |
| ComputePricingModel | ONDEMAND | SPOT for up to ~70% savings on fault-tolerant batch jobs |
| MaxComputeNodes | 10 | Increase or decrease as needed |
| CapacityBlockId | (blank) | Required if using P-series GPU instances (p4/p5/p6) — obtain a reservation in the EC2 console first |
| EfsFileSystemId | (blank) | Provide an existing EFS ID to persist data across cluster lifecycles. Otherwise, an EFS volume is auto-created |
| S3BucketName | (blank) | Grant the cluster read/write access to a specific S3 bucket |
| FsxLustreFileSystemId | (blank) | Mount an existing FSx for Lustre filesystem for high-throughput I/O |
| KeyPairName | (blank) | Provide if you want SSH access in addition to Session Manager |

Deployment takes 15-25 minutes.

### 3. Connect

Three options depending on what you enabled. All connection details are in the CloudFormation stack outputs after deployment.

**Session Manager (default — no key pair needed):**

Requires the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed locally with [credentials configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html) (`aws configure sso` for IAM Identity Center, or `aws configure` for access keys), plus the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html).

```bash
# Log in to AWS first (if using IAM Identity Center)
aws sso login --profile your-profile

# Connect to head node
aws ssm start-session --target INSTANCE_ID --region REGION
```

You'll land as `ssm-user`. If AD is configured for [multi-user access](#multi-user-access), switch to your identity with `su - yourusername`.

**DCV Remote Desktop (when enabled):**

Open `https://ELASTIC_IP:8443` in a browser. Your browser will show a certificate warning (DCV uses a self-signed certificate by default — this is expected and safe to accept). Log in as `ec2-user` (Amazon Linux) or `ubuntu` (Ubuntu) with the password you set during deployment. If AD is configured, log in with your AD credentials directly — no extra step.

Bookmark the URL — the Elastic IP never changes, even after stopping and starting the head node.

**SSH (when key pair provided):**

```bash
ssh -i ~/.ssh/your-key.pem ec2-user@ELASTIC_IP
```

If AD is configured, you can SSH as your AD username directly.

### 4. Submit a Job

```bash
# Check cluster status
sinfo

# Submit a simple job
sbatch --wrap="hostname && sleep 10"

# Check job status
squeue

# View output when complete
cat slurm-*.out
```

Compute nodes launch automatically on job submission and terminate after 10 minutes idle.

## Updating the Cluster

There are two ways to modify a running cluster, depending on what you're changing:

**CloudFormation stack update** — for template parameters (instance types, max nodes, DCV settings, storage). Go to CloudFormation → select your stack → Update → use current template → change parameters. This updates the wrapper resources and triggers a ParallelCluster update for cluster config changes.

**`pcluster update-cluster`** — for cluster configuration changes that aren't exposed as template parameters (adding queues, AD integration, login nodes). Requires the [ParallelCluster CLI](#install-the-parallelcluster-cli). See [Post-Deploy Customization](#post-deploy-customization) below.

Some changes require the compute fleet to be stopped first (e.g., changing instance types). ParallelCluster will tell you if a stop is needed — run with `--dryrun` first to check:

```bash
pcluster update-cluster --cluster-name CLUSTER_NAME --region REGION \
  --cluster-configuration cluster-config.yaml --dryrun true
```

## Post-Deploy Customization

The template deploys a single compute queue. Use `pcluster update-cluster` to add queues, users, or login nodes after deployment.

### Install the ParallelCluster CLI

```bash
pip install aws-parallelcluster
```

### Export the current config

```bash
pcluster export-cluster-config --cluster-name CLUSTER_NAME --region REGION > cluster-config.yaml
```

### Adding a GPU Queue

Edit `cluster-config.yaml` and add a second queue under `SlurmQueues`:

```yaml
SlurmQueues:
  - Name: compute
    # ... existing queue config ...
  - Name: gpu
    CapacityType: ONDEMAND
    ComputeResources:
      - Name: gpu-nodes
        InstanceType: g6.12xlarge
        MinCount: 0
        MaxCount: 4
    Networking:
      SubnetIds:
        - subnet-xxxxxxxx  # same compute subnet
```

Apply:

```bash
pcluster update-cluster --cluster-name CLUSTER_NAME --region REGION \
  --cluster-configuration cluster-config.yaml
```

Researchers target the GPU queue with `sbatch -p gpu job.sh`.

### Adding a High-Memory Queue

```yaml
  - Name: highmem
    CapacityType: ONDEMAND
    ComputeResources:
      - Name: highmem-nodes
        InstanceType: r7i.8xlarge
        MinCount: 0
        MaxCount: 4
    Networking:
      SubnetIds:
        - subnet-xxxxxxxx
```

### Multi-User Access

By default, the cluster has a single OS user (`ec2-user` on Amazon Linux, `ubuntu` on Ubuntu). For multiple researchers sharing a cluster, connect to an Active Directory via LDAP — this is the only multi-user method ParallelCluster supports. Identity providers like Okta or IAM Identity Center don't integrate directly, but if your institution's Okta is backed by AD (common at universities), ParallelCluster connects to that underlying AD.

#### Recommended: Active Directory / LDAP Integration

You need an AD endpoint reachable from the cluster VPC. Two options:

| Option | Best for | Cost | Requires |
|--------|----------|------|----------|
| [AWS Managed Microsoft AD](https://docs.aws.amazon.com/directoryservice/latest/admin-guide/directory_microsoft_ad.html) | Institutions without existing AD, or wanting a standalone directory in AWS | ~$146/month (Standard) | Nothing — fully managed, runs in your VPC |
| [AD Connector](https://docs.aws.amazon.com/directoryservice/latest/admin-guide/directory_ad_connector.html) | Institutions with existing on-prem AD | ~$48/month (Small) | VPN or Direct Connect to campus network |

For most research institutions, **AWS Managed Microsoft AD** is the simpler path — no VPN dependency, works standalone, and can also serve as the identity source for [IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/what-is.html) (giving researchers SSO to the AWS console). See the [ParallelCluster multi-user tutorial](https://docs.aws.amazon.com/parallelcluster/latest/ug/tutorials_05_multi-user-ad.html) for a full walkthrough.

Once AD is set up, add a `DirectoryService` section to your cluster config:

```yaml
DirectoryService:
  DomainName: dc=university,dc=edu
  DomainAddr: ldaps://ad.university.edu
  PasswordSecretArn: arn:aws:secretsmanager:REGION:ACCOUNT:secret:ad-bind-password
  DomainReadOnlyUser: cn=ReadOnly,ou=Users,dc=university,dc=edu
  GenerateSshKeysForUsers: true
```

This requires:

- An Active Directory reachable from the cluster VPC (AWS Managed Microsoft AD or on-prem AD via AD Connector)
- A Secrets Manager secret containing the bind user password
- LDAPS (port 636) open between the cluster and the AD endpoint

Once configured, users log in with their institutional credentials. ParallelCluster creates home directories automatically and Slurm associates jobs with the authenticated user.

**Slurm accounting (optional but recommended for chargeback):** By default, Slurm tracks jobs in the current session but doesn't persist historical data. For per-user job reporting, grant chargeback, and fair-share scheduling, configure [Slurm accounting](https://docs.aws.amazon.com/parallelcluster/latest/ug/slurm-accounting-v3.html) with an external database (e.g., Amazon RDS MySQL). This enables `sacct` queries like "how many CPU-hours did each researcher use this month" — essential for institutions that charge compute costs back to grants. DCV and SSH authenticate against AD directly. Session Manager still lands as `ssm-user` (IAM-authenticated), so users need to `su - username` after connecting.

#### Not recommended: Manual user creation

For quick testing or very small teams (2-3 people), you can create users manually on the head node:

```bash
sudo useradd -m researcher1
sudo passwd researcher1
```

This doesn't scale, has no central identity management, and creates a password management burden. Use AD for anything beyond quick experiments.

### Login Nodes

Login nodes are dedicated instances that handle user SSH/DCV sessions, keeping the head node focused on running the Slurm controller. They're optional and most clusters don't need them initially.

**When to consider login nodes:**

- Multiple users running DCV desktop sessions (GUI apps consume significant CPU/memory on the head node)
- Users running GPU-accelerated desktop applications (visualization, rendering) — use G-series login nodes instead of burning compute queue hours
- Head node showing high CPU/memory usage from user sessions (check the [CloudWatch dashboard](#monitoring))

**When you don't need them:**

- Single user or small team primarily submitting batch jobs via SSH
- DCV is disabled (CLI-only access is lightweight)
- Head node metrics show plenty of headroom

**Sizing guidance:**

Most clusters start without login nodes — the head node handles everything. Add login nodes when the head node becomes a bottleneck.

| Scenario | Login nodes needed? | Recommendation |
|----------|-------------------|----------------|
| 1-3 users, CLI/SSH only | No | m7i.large head node — Slurm controller + shell sessions need minimal resources |
| 1-3 users, DCV desktop, no GPU apps | No | m7i.2xlarge head node — desktop sessions need more CPU/memory for the window manager |
| 4+ users with DCV, or head node showing resource pressure | Yes | m7i.xlarge login nodes — offloads desktop sessions from the head node |
| Users running GPU desktop apps (visualization, rendering) | Yes | g6.xlarge login nodes — GPU-accelerated desktop without using the compute queue |

Start with 1 login node. Add a second for redundancy or if the first shows resource pressure.

To add login nodes without DCV:

```yaml
LoginNodes:
  Pools:
    - Name: login
      Count: 2
      InstanceType: m7i.xlarge
      Networking:
        SubnetIds:
          - subnet-xxxxxxxx  # same as head node subnet
      Ssh:
        KeyName: your-key-pair  # optional
```

This gives users CLI/SSH access to login nodes with shared storage mounted automatically. No additional setup needed.

To also enable DCV on login nodes, add `Dcv`, `CustomActions`, and `Iam` sections so the bootstrap script installs the desktop environment and retrieves the DCV password:

```yaml
LoginNodes:
  Pools:
    - Name: login
      Count: 2
      InstanceType: m7i.xlarge
      Networking:
        SubnetIds:
          - subnet-xxxxxxxx
      Dcv:
        Enabled: true
        AllowedIps: 203.0.113.0/24  # your office CIDR
      Iam:
        AdditionalIamPolicies:
          - Policy: arn:aws:iam::aws:policy/SecretsManagerReadWrite
      CustomActions:
        OnNodeConfigured:
          Script: s3://BOOTSTRAP_BUCKET/bootstrap.sh  # same bucket from template outputs
          Args:
            - 'yes'
            - 'SECRET_ARN'  # from Secrets Manager console
```

Replace `BOOTSTRAP_BUCKET` and `SECRET_ARN` with the values from your CloudFormation stack resources.

Users connect to login nodes via a load-balanced DNS endpoint that ParallelCluster creates automatically.

## Cost Management

### Stop/Start the Head Node

The head node runs 24/7. When the cluster isn't in use, stop it to save costs:

```bash
# Stop
aws ec2 stop-instances --instance-ids INSTANCE_ID

# Start
aws ec2 start-instances --instance-ids INSTANCE_ID
```

The Elastic IP stays assigned — your DCV URL and SSH command don't change after restart.

### Compute Node Costs

Compute nodes only run when jobs are queued. They terminate automatically after 10 minutes idle (`ScaledownIdletime: 10`). No jobs = no compute cost.

### Spot Instances

Set `ComputePricingModel` to `SPOT` for up to 70% savings on compute nodes. Spot instances can be interrupted — Slurm automatically requeues affected jobs. Good for fault-tolerant batch workloads, not for long-running interactive sessions.

### EFS Costs

If the template creates a new EFS (no `EfsFileSystemId` provided), it's billed at ~$0.30/GB/month with bursting throughput. Data is deleted when the cluster is deleted. For persistent data, use an existing EFS or S3.

### Cluster Overhead

ParallelCluster creates supporting resources (CloudWatch dashboard, Route 53 hosted zone, DynamoDB table, Lambda functions) that cost roughly $4-5/month regardless of usage. These are managed by ParallelCluster and cleaned up when the cluster is deleted.

## Monitoring

ParallelCluster automatically creates a [CloudWatch dashboard](https://docs.aws.amazon.com/parallelcluster/latest/ug/cloudwatch-dashboard-v3.html) for each cluster with head node metrics (CPU, memory, disk), storage metrics, and cluster health. It also sets up alarms for disk and memory usage. Find it in the CloudWatch console under Dashboards → `parallelcluster-CLUSTER_NAME-REGION`.

Cluster logs (Slurm scheduler, DCV, system) are streamed to CloudWatch Logs automatically under the log group `/aws/parallelcluster/CLUSTER_NAME`.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cluster creation fails | Check CloudFormation events tab for the error. Common: invalid subnet, insufficient IAM permissions. |
| DCV not accessible | Verify `DCVAllowedIps` includes your IP. Check security group allows port 8443. |
| Compute nodes not launching | Run `sinfo` — nodes should show as `idle~` (powered down). Submit a job to trigger scaling. Check `/var/log/parallelcluster/slurm_resume.log` on head node. |
| Bootstrap script failed | Check `/var/log/bootstrap.log` on the head node. |
| Session Manager not connecting | Verify [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) are installed. Run `aws sts get-caller-identity` to confirm credentials are working. |
| Spot instances interrupted | Slurm requeues jobs automatically. Check `squeue` for requeued jobs. |
