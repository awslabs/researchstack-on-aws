# Frequently Asked Questions

## Getting Started

**What do I need before deploying any template?**
Most compute templates require a VPC and subnet. If your institution doesn't provide one, deploy `research-vpc.yaml` first — it creates a ready-to-use network. You'll also need the [AWS CLI](https://aws.amazon.com/cli/) installed (or use the [CloudFormation console](https://console.aws.amazon.com/cloudformation/home#/stacks/create) directly). See the [Templates README](../templates/README.md#getting-started) for details.

**What's the difference between deploying standalone vs Service Catalog?**
Standalone means you deploy templates directly via the CloudFormation console or CLI — simplest for single accounts and small teams. Service Catalog adds a governance layer for multi-account institutions: IT admins publish templates as products in a catalog, researchers browse and click "Launch" without needing CloudFormation knowledge. Both use the same templates. See the [Service Catalog Deployment Guide](service-catalog-guide.md) if you need multi-account governance.

**Which template should I start with?**
See the [Research Lifecycle Guide](research-lifecycle-guide.md) — it maps each phase of a research project to the right templates. If you just want to get going: deploy a VPC (`research-vpc.yaml`), then an EC2 instance (`ec2-general-purpose.yaml`).

## Connecting to Resources

**How do I connect to my EC2 instance?**
All EC2 templates use [SSM Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html) by default — no SSH keys, no open ports, no public IP needed. After deployment, find the connect command in the stack outputs:
```bash
aws ssm start-session --target i-0123456789abcdef0 [--profile your-profile-name]
```
Requires the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) for the AWS CLI.

**Why Session Manager instead of SSH?**
SSM is more secure (no inbound ports, no key management, no public IP required) and works through the AWS CLI without any network configuration. SSH is available as an option if you need it for file transfers (SCP/SFTP), VS Code Remote development, or port forwarding — just provide a key pair and allowed IP range when deploying.

**How do I transfer files to/from my instance?**
Several options:
- **S3**: Grant the instance access to an S3 bucket (via the `S3BucketName` parameter), then use `aws s3 cp` from the instance
- **EFS**: Mount shared storage (via the `EfsFileSystemId` parameter) accessible from multiple instances
- **SCP/SFTP**: Provide a key pair when deploying, then use `scp` or `sftp` from your local machine
- **SSM port forwarding**: `aws ssm start-session --target INSTANCE_ID --document-name AWS-StartPortForwardingSession --parameters portNumber=22,localPortNumber=2222` then `scp -P 2222 file.txt localhost:`

**How do I access SageMaker Studio?**
SageMaker Studio is a managed Jupyter environment — you access it through the [SageMaker console](https://console.aws.amazon.com/sagemaker/), not via SSH or SSM. After deploying the template, an admin assigns users or [IAM Identity Center](https://aws.amazon.com/iam/identity-center/) groups to the domain in the SageMaker console under **Domains** → your domain → **User profiles**. Assigned users then see a "Launch" button next to the domain.

**What is SageMaker Studio?**
[Amazon SageMaker Studio](https://aws.amazon.com/sagemaker/studio/) is a managed environment for machine learning and data science. It provides Jupyter notebooks, code editors, and GPU-accelerated compute — all in the browser, with no infrastructure to manage. You don't install anything locally; the compute runs in AWS and shuts down automatically when idle.

**How do I connect to my ParallelCluster?**
Three options: SSM Session Manager (default, no keys needed), DCV remote desktop (if enabled — full GUI via web browser), or SSH (if a key pair was provided). All connection details are in the stack outputs. See the [ParallelCluster Guide](parallelcluster-guide.md#3-connect) for step-by-step instructions.

## Cost and Billing

**How do I track costs per project or grant?**
Every resource deployed by ResearchStack is automatically tagged with `Project`, `CostCenter`, and `Owner`. Use [AWS Cost Explorer](https://console.aws.amazon.com/cost-management/home#/cost-explorer) to filter by these tags. You must first [activate cost allocation tags](cost-optimization-guide.md#activating-cost-allocation-tags) in the Billing console (one-time setup). See the [Cost Optimization Guide](cost-optimization-guide.md) for full details.

**How do I set up budget alerts?**
Deploy the `budget-alert.yaml` template with your cost center and monthly budget amount. You'll get email alerts at 50%, 80%, and 100% of your budget. See the [Cost Optimization Guide](cost-optimization-guide.md#budget-alerts) for deployment instructions.

**Will my instances stop automatically if I forget?**
EC2 templates include idle shutdown by default — instances are automatically stopped after 90 minutes of low CPU utilization. ParallelCluster compute nodes auto-terminate after 10 minutes idle. The ParallelCluster head node does not auto-stop (it runs the Slurm scheduler) — stop it manually when the cluster isn't in use.

**Does F&A overhead apply to cloud costs?**
This is changing. The Consolidated Appropriations Act, 2026 (P.L. 119-75) directs OMB to exclude cloud computing from F&A, matching on-premises equipment treatment. Check with your grants office for your institution's current policy. See [F&A and Cloud Computing](cost-optimization-guide.md#fa-and-cloud-computing) for details.

## Templates and Configuration

**Can I use my own AMI?**
Yes. The EC2 templates use [SSM parameter paths](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html) for AMI lookup. You can store a custom AMI ID in SSM at a convention path and add it to the template's `AllowedValues` list. The SSM value can be updated anytime without redeploying the template.

**Can I use Spot Instances?**
ParallelCluster supports Spot natively — set `ComputePricingModel` to `SPOT` for up to 70% savings on compute nodes. Standalone EC2 templates don't currently support Spot (this is on the roadmap). See the [Cost Optimization Guide](cost-optimization-guide.md#compute-optimization) for Spot guidance.

**What if I need an instance type that's not in the allowed pattern?**
The templates use regex patterns (e.g., `^m[0-9]+[a-z]*\.`) to allow any current or future instance within a family. If you need a different family entirely, use the template that matches your workload (C-series for compute, R-series for memory, G-series for GPU). For instance types outside these families, you'd need to modify the template's `AllowedPattern`.

**How do I delete my resources?**
Delete the CloudFormation stack — this removes all resources the template created. Via console: [CloudFormation](https://console.aws.amazon.com/cloudformation/) → select stack → Delete. Via CLI: `aws cloudformation delete-stack --stack-name STACK_NAME`. For Service Catalog products, go to **Provisioned products** → select → **Actions** → **Terminate**. See the [main README](../README.md#deleting-resources) for more.

## Security and Access

**Who can access resources I deploy?**
By default, only users with access to the AWS account can see or manage deployed resources. EC2 instances are accessible via SSM Session Manager (which uses IAM permissions) or SSH (if a key pair is provided). S3 buckets are private by default. For multi-account setups, see the [access control guidance](../README.md#cost-tracking-and-access-control).

**Is my data encrypted?**
Yes. All templates enable encryption by default — S3 uses AES-256 server-side encryption, EBS volumes use gp3 with encryption enabled, EFS enforces TLS in transit, and FSx Lustre encrypts at rest. No action needed.

**Do I need IAM Identity Center?**
IDC is recommended but not required for most templates. The SageMaker Studio template requires IDC (it uses SSO auth mode). For standalone EC2, S3, EFS, and VPC deployments, any IAM credentials work. IDC becomes important for Service Catalog governance and multi-account access management. See the [main README](../README.md#cost-tracking-and-access-control) for recommendations.
