# Examples

## Researcher IAM Policy

`researcher-policy.json` — A least-privilege IAM policy for researchers using ResearchStack. Grants access to:

- Browse and launch Service Catalog products
- Connect to EC2 instances via SSM Session Manager
- View CloudFormation stack outputs (connection details, resource IDs)
- Read/write S3 data on ResearchStack-managed buckets
- View costs and budgets in Cost Explorer

This policy does not grant admin access, direct EC2 launch permissions, or IAM management — researchers deploy infrastructure through Service Catalog, which uses launch roles with scoped permissions.

### How to use

**As an IAM Identity Center (IDC) permission set** — recommended for organizations using SSO:

1. Go to [IAM Identity Center → Permission sets](https://console.aws.amazon.com/singlesignon/home#/permissionSets)
2. Create a custom permission set
3. Paste the policy JSON as an inline policy
4. Assign the permission set to researcher users/groups for the target accounts

See the [AWS IDC documentation](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html) for details.

**As a standalone IAM role** — for accounts not using IDC:

1. Create an IAM role with this policy attached
2. To share across multiple accounts in an OU, deploy the role via [CloudFormation StackSets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html)

For admin access, use the AWS-managed `AdministratorAccess` policy — no custom policy needed.
