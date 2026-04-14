"""IAM launch role for a Service Catalog product.

Creates a role that SC assumes to launch CloudFormation stacks on behalf of users.
One role per product for least-privilege. Always includes CloudFormationFullAccess
plus whatever managed policies the product declares.
"""

from typing import Dict, List, Optional

from aws_cdk import CfnOutput
from aws_cdk import aws_iam as iam
from constructs import Construct

from utils.resource_naming import ServiceCatalogRoleNaming


class LaunchRoleConstruct(Construct):
    """Creates an IAM role for SC launch constraints."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        product_name: str,
        portfolio_name: str,
        managed_policy_names: Optional[List[str]] = None,
        custom_policy: Optional[List[Dict]] = None,
    ) -> None:
        super().__init__(scope, construct_id)

        role_name = ServiceCatalogRoleNaming.get_launch_role_name(
            product_name=product_name,
            portfolio_name=portfolio_name,
        )

        policies = list(managed_policy_names or [])
        if "AWSCloudFormationFullAccess" not in policies:
            policies.append("AWSCloudFormationFullAccess")

        # S3 access for SC template artifacts
        inline_policies: Dict[str, iam.PolicyDocument] = {
            "S3AssetsBucketAccess": iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["s3:GetObject"],
                        resources=["*"],
                        conditions={
                            "StringEquals": {
                                "s3:ExistingObjectTag/servicecatalog:provisioning": "true",
                            },
                        },
                    ),
                ]
            ),
        }

        # Custom inline policy statements from TOML
        if custom_policy:
            inline_policies["CustomPolicy"] = iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW if stmt.get("effect", "Allow") == "Allow" else iam.Effect.DENY,
                        actions=stmt["actions"],
                        resources=stmt["resources"],
                    )
                    for stmt in custom_policy
                ]
            )

        self.role = iam.Role(
            self,
            "LaunchRole",
            role_name=role_name,
            assumed_by=iam.ServicePrincipal("servicecatalog.amazonaws.com"),
            description=f"SC launch role for {product_name} in {portfolio_name}",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(name)
                for name in policies
            ],
            inline_policies=inline_policies,
        )

        CfnOutput(self, "LaunchRoleArn", value=self.role.role_arn)
