# ParallelCluster HPC Guide

Deploy and operate a Slurm HPC cluster on AWS using the ResearchStack's ParallelCluster template.

## What the Template Provides

The template deploys a production-ready HPC cluster with one CloudFormation stack:

- **Slurm scheduler** with one auto-scaling compute queue (nodes launch on job submission, terminate when idle)
- **Shared EFS storage** at `/shared` — a managed network file system (NFS) accessible from all cluster nodes. Auto-created with the cluster, or bring an existing EFS.
- **Optional DCV remote desktop** for GUI access via web browser
- **Elastic IP** so the head node IP address never changes across stop/start cycles
- **Session Manager access** (no SSH keys required)
- **Cost tracking tags** on all resources (Project, CostCenter, Owner)

The cluster has two OS users: `ec2-user` (Amazon Linux) or `ubuntu` (Ubuntu) is the default user for SSH and DCV login, and `ssm-user` is the user you land as when connecting via Session Manager (it has sudo access and Slurm commands in its PATH). Both users can run Slurm commands and are fine for day-to-day use. When AD is configured for multi-user, each researcher logs in with their own credentials.

After deployment, you can expand the cluster with additional compute queues, multi-user access via Active Directory, login nodes, and more — see [Updating and Customizing the Cluster](#updating-and-customizing-the-cluster).

## Quick Start

### 1. Prerequisites

- A VPC with a public subnet (head node) and a private subnet (compute nodes). The private subnet needs a NAT Gateway in the public subnet for internet access. Deploy the `research-vpc.yaml` template first if you don't have one.
- An EC2 key pair — only if you want SSH access. [Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html) and [DCV remote desktop](https://docs.aws.amazon.com/dcv/latest/userguide/what-is-dcv.html) work without one. Session Manager lets you connect to instances through the AWS CLI or console without opening inbound ports or managing SSH keys. DCV provides a full GUI desktop accessible via web browser.

### 2. Deploy

Deploy via the CloudFormation console, CLI, or Service Catalog.

**Required parameters:**

| Parameter | What to enter |
|-----------|---------------|
| ProjectName | Your research project name (e.g., `genomics-lab`) |
| CostCenter | Department or grant number for billing |
| HeadNodeSubnetId | A public subnet (one with a route to an internet gateway) |
| ComputeSubnetId | A private subnet (in the same VPC). It needs a route to a NAT Gateway in the public subnet for internet access. If unsure, use the same public subnet as the head node — it works, but a private subnet is more secure. |

**DCV parameters (when EnableDCV = yes):**

| Parameter | What to enter |
|-----------|---------------|
| DCVAllowedIps | Your office/campus CIDR (e.g., `203.0.113.0/24`). Use `0.0.0.0/0` to allow access from anywhere. |
| DCVPassword | Password for the DCV desktop login. Min 8 characters. You can change it later by connecting to the head node and running `sudo passwd ec2-user` (or `sudo passwd ubuntu` on Ubuntu). |

**Optional configuration — safe to leave as defaults:**

| Parameter | Default | When to change |
|-----------|---------|----------------|
| ClusterName | (required) | Choose a unique name per account/region (e.g., `genomics-cluster`, `cfd-team`) |
| OperatingSystem | alinux2023 | Ubuntu 22.04/24.04 if your software requires it |
| HeadNodeInstanceType | m7i.2xlarge | Larger if running DCV with heavy GUI apps, smaller (e.g., m7i.large) if CLI-only |
| ComputeInstanceType | c7i.8xlarge | Match to your workload: R-series for memory, G-series for GPU, Hpc-series for tightly-coupled MPI. See the [EC2 Instance Type Explorer](https://aws.amazon.com/ec2/instance-explorer/) for family overviews, or [Vantage](https://instances.vantage.sh/?id=421e512ec7fc071920ffc00ca2bc7141ef1c98aa) to compare specs and pricing side-by-side. |
| ComputePricingModel | ONDEMAND | [SPOT](https://aws.amazon.com/ec2/spot/) for up to ~70% savings — uses spare EC2 capacity at a discount but instances can be interrupted with 2 min notice. Use On-Demand for critical workloads. |
| MaxComputeNodes | 10 | Increase or decrease as needed |
| CapacityBlockId | (blank) | Required if using P-series GPU instances (p4/p5/p6) — [obtain a Capacity Block reservation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/capacity-blocks-purchase.html) in the EC2 console first |
| EfsFileSystemId | (blank) | Provide an existing EFS ID to persist data across cluster lifecycles. Otherwise, an EFS volume is auto-created |
| S3BucketName | (blank) | Grant the cluster read/write access to a specific S3 bucket |
| FsxLustreFileSystemId | (blank) | Mount an existing FSx for Lustre filesystem for high-throughput I/O |
| KeyPairName | (blank) | Provide if you want SSH access in addition to Session Manager. [Create a key pair](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html) in the EC2 console if you don't have one. |

Deployment takes 15-25 minutes.

### 3. Connect

There are three options for connecting to your cluster, depending on what you enabled. All connection details (Head Node / Elastic IP address, Head Node Instance ID, Session Manager command, DCV URL, SSH command) are in the CloudFormation stack **Outputs** tab after deployment.

**Session Manager (default — no key pair needed):**

Requires the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed locally with [credentials configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html) (`aws configure sso` for IAM Identity Center, or `aws configure` for [IAM access keys](https://docs.aws.amazon.com/cli/latest/userguide/cli-authentication-user.html)), plus the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html).

```bash
# Log in to AWS first (if using IAM Identity Center)
aws sso login --profile your-profile

# Connect (copy the full command from stack Outputs tab)
aws ssm start-session --target HEAD_NODE_INSTANCE_ID --region REGION
```

You'll land as `ssm-user` with sudo access. Slurm commands (`sinfo`, `sbatch`, etc.) are available. If AD is configured for [multi-user access](#multi-user-access), switch to your identity with `su - yourusername`.

**DCV Remote Desktop (when enabled):**

Open the DCV URL from the stack Outputs tab (e.g., `https://ELASTIC_IP:8443`) in a browser. Your browser will show a certificate warning — DCV uses a self-signed certificate, meaning the connection is encrypted (HTTPS) but the certificate isn't issued by a trusted CA (like Let's Encrypt or ACM), so your browser can't verify the server's identity. This is expected and safe to accept. Log in as `ec2-user` (Amazon Linux) or `ubuntu` (Ubuntu) with the password you set during deployment. If AD is configured, log in with your AD credentials directly.

Bookmark the URL — the Elastic IP never changes, even after stopping and starting the head node.

**SSH (when key pair provided):**

```bash
# Copy the SSH command from stack Outputs tab
ssh -i ~/.ssh/your-key.pem ec2-user@ELASTIC_IP
```

If AD is configured, you can SSH as your AD username directly rather than ec2-user.

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

## Updating and Customizing the Cluster

### CloudFormation Stack Update

For changes to template parameters (instance types, max nodes, DCV settings, storage): go to CloudFormation → select your stack → Update → use current template → change parameters.

### ParallelCluster CLI

For changes beyond what the template exposes — adding queues, AD integration, login nodes — use the [ParallelCluster CLI](https://docs.aws.amazon.com/parallelcluster/latest/ug/install-v3-parallelcluster.html). All cluster configuration changes are made by editing a [YAML config file](https://docs.aws.amazon.com/parallelcluster/latest/ug/cluster-configuration-file-v3.html) and applying it with `pcluster update-cluster`.

Install the CLI:

```bash
pip install aws-parallelcluster
```

Export your cluster's current config:

```bash
pcluster export-cluster-config --cluster-name CLUSTER_NAME --region REGION > cluster-config.yaml
```

Edit `cluster-config.yaml` with your changes (see examples below), then apply:

```bash
# Preview changes first (recommended)
pcluster update-cluster --cluster-name CLUSTER_NAME --region REGION \
  --cluster-configuration cluster-config.yaml --dryrun true

# Apply changes
pcluster update-cluster --cluster-name CLUSTER_NAME --region REGION \
  --cluster-configuration cluster-config.yaml
```

Some changes require the compute fleet to be stopped first (e.g., changing instance types). The `--dryrun` output will tell you if a stop is needed.

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

By default, the cluster has two OS users — `ec2-user` (or `ubuntu` on Ubuntu) for SSH/DCV and `ssm-user` for Session Manager — but no multi-user support. For multiple researchers sharing a cluster, connect to an Active Directory via LDAP — this is the only multi-user method ParallelCluster supports. Identity providers like Okta or IAM Identity Center don't integrate directly, but if your institution's Okta is backed by AD, ParallelCluster connects to that underlying AD.

#### Recommended: Active Directory / LDAP Integration

You need an AD endpoint reachable from the cluster VPC. Two options:

| Option | Best for | Cost | Requires |
|--------|----------|------|----------|
| [AWS Managed Microsoft AD](https://docs.aws.amazon.com/directoryservice/latest/admin-guide/directory_microsoft_ad.html) | Institutions without existing AD, or wanting to replicate on-prem AD to AWS for high availability | ~$86/month (Standard, 2 DCs). See [pricing](https://aws.amazon.com/directoryservice/pricing/). | Nothing other than a VPC — fully managed, multi-AZ, runs in your VPC |
| [AD Connector](https://docs.aws.amazon.com/directoryservice/latest/admin-guide/directory_ad_connector.html) | Institutions with existing on-prem AD wanting to proxy requests to AWS without replicating the directory (availability depends on your on-prem AD and network link) | ~$36/month (Small). See [pricing](https://aws.amazon.com/directoryservice/other-directories-pricing/). | VPN or Direct Connect to campus network |

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

**Slurm accounting (optional but recommended for chargeback):** By default, Slurm tracks jobs in the current session but doesn't persist historical data. For per-user job reporting, grant chargeback, and fair-share scheduling, configure [Slurm accounting](https://docs.aws.amazon.com/parallelcluster/latest/ug/slurm-accounting-v3.html) with an external database (e.g., Amazon RDS MySQL). This enables `sacct` queries like "how many CPU-hours did each researcher use this month" — essential for institutions that charge compute costs back to grants.

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
- Users running GPU-accelerated desktop applications (visualization, rendering) — G-series login nodes provide a GPU desktop for interactive work without submitting jobs to the compute queue
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

Start with 1 login node. ParallelCluster load-balances users across login nodes automatically, so add more as user count grows or if the first shows resource pressure.

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
        AllowedIps: 0.0.0.0/0  # restrict to your office CIDR for security
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

Find `BOOTSTRAP_BUCKET` and `SECRET_ARN` in the CloudFormation stack **Outputs** tab (`BootstrapBucketName` and `DCVPasswordSecretArn`).

## Cost Management

### Stop/Start the Head Node

The head node runs 24/7. When the cluster isn't in use, stop it to save costs:

```bash
# Stop
aws ec2 stop-instances --instance-ids HEAD_NODE_INSTANCE_ID

# Start
aws ec2 start-instances --instance-ids HEAD_NODE_INSTANCE_ID
```

The Elastic IP stays assigned — your DCV URL and SSH command don't change after restart.

Note: the head node instance ID also remains the same across stop/start cycles. It only changes if the instance is terminated and replaced.

### Compute Node Costs

Compute nodes only run when jobs are queued. They terminate automatically after 10 minutes idle (`ScaledownIdletime: 10`). No jobs = no compute cost. See [EC2 pricing](https://aws.amazon.com/ec2/pricing/) for per-instance rates.

### Spot Instances

Set `ComputePricingModel` to `SPOT` for up to 70% savings on compute nodes. Slurm automatically requeues interrupted jobs. Good for fault-tolerant batch workloads, not for long-running interactive sessions. See [Spot pricing](https://aws.amazon.com/ec2/spot/pricing/).

### EFS Costs

If the template creates a new EFS (no `EfsFileSystemId` provided), it's billed at ~$0.30/GB/month for data stored, with bursting throughput. An empty EFS costs nothing. Data is deleted when the cluster is deleted. For persistent data, use an existing EFS or S3. See [EFS pricing](https://aws.amazon.com/efs/pricing/).

### Cluster Overhead

ParallelCluster creates supporting resources (CloudWatch dashboard, Route 53 hosted zone, DynamoDB table, Lambda functions, S3 bucket for bootstrap scripts) that cost roughly $4-5/month regardless of usage. These are managed by ParallelCluster and cleaned up when the cluster is deleted.

## Monitoring

ParallelCluster automatically creates a [CloudWatch dashboard](https://docs.aws.amazon.com/parallelcluster/latest/ug/cloudwatch-dashboard-v3.html) for each cluster with head node metrics (CPU, memory, disk), storage metrics, and cluster health. It also sets up alarms for disk and memory usage. Find it in the CloudWatch console under Dashboards → `parallelcluster-CLUSTER_NAME-REGION`.

Cluster logs (Slurm scheduler, DCV, system) are streamed to CloudWatch Logs automatically under the log group `/aws/parallelcluster/CLUSTER_NAME`.

## Deleting the Cluster

When you're done with the cluster, delete the CloudFormation stack to clean up all resources (head node, compute nodes, EFS if auto-created, security groups, Elastic IP, bootstrap bucket, Lambda functions).

**Via AWS Console**: Go to [CloudFormation](https://console.aws.amazon.com/cloudformation/) → select the cluster stack → **Delete**.

**Via AWS CLI**:
```bash
aws cloudformation delete-stack --stack-name STACK_NAME
```

Deletion takes 10-15 minutes. If you provided an existing EFS (`EfsFileSystemId`) or FSx Lustre filesystem, those persist independently — only auto-created storage is deleted with the stack.

If the stack deletion fails (common cause: the ParallelCluster cluster is still in a transitional state), wait a few minutes and retry. Check the CloudFormation events tab for the specific error.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cluster creation fails | Check CloudFormation events tab for the error. Common: invalid subnet, insufficient IAM permissions. |
| DCV not accessible | Verify `DCVAllowedIps` includes your IP. Check security group allows port 8443. |
| Compute nodes not launching | Run `sinfo` — nodes should show as `idle~` (powered down). Submit a job to trigger scaling. Check `/var/log/parallelcluster/slurm_resume.log` on head node. |
| Bootstrap script failed | Check `/var/log/bootstrap.log` on the head node. |
| Session Manager not connecting | Verify [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) are installed. Run `aws sts get-caller-identity` to confirm credentials are working. |
| Spot instances interrupted | Slurm requeues jobs automatically. Check `squeue` for requeued jobs. |
