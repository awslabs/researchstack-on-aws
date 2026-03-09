"""Share a Service Catalog portfolio with an AWS Organizations OU.

Uses a CDK custom resource to call the SC API directly, since the L2
construct doesn't support OU-level sharing with tag options and principals.
"""

import enum

from aws_cdk import Duration
from aws_cdk import aws_iam as iam
from aws_cdk import aws_servicecatalog as sc
from aws_cdk.custom_resources import (
    AwsCustomResource,
    AwsCustomResourcePolicy,
    AwsSdkCall,
    PhysicalResourceId,
)
from constructs import Construct


class OrganizationNodeType(enum.Enum):
    ORGANIZATION = "ORGANIZATION"
    ORGANIZATIONAL_UNIT = "ORGANIZATIONAL_UNIT"
    ACCOUNT = "ACCOUNT"


class PortfolioShare(Construct):
    """Shares a SC portfolio with an org node (OU or root)."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        portfolio: sc.Portfolio,
        organization_node_type: OrganizationNodeType,
        organization_node_value: str,
        share_tag_options: bool = False,
        share_principals: bool = False,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        physical_id = PhysicalResourceId.of(
            f"{portfolio.portfolio_id}-{organization_node_type.value}-{organization_node_value}"
        )
        node_param = {
            "Type": organization_node_type.value,
            "Value": organization_node_value,
        }

        create_call = AwsSdkCall(
            service="ServiceCatalog",
            action="createPortfolioShare",
            parameters={
                "PortfolioId": portfolio.portfolio_id,
                "OrganizationNode": node_param,
                "ShareTagOptions": share_tag_options,
                "SharePrincipals": share_principals,
            },
            physical_resource_id=physical_id,
            ignore_error_codes_matching="ResourceNotFoundException",
        )

        update_call = AwsSdkCall(
            service="ServiceCatalog",
            action="updatePortfolioShare",
            parameters={
                "PortfolioId": portfolio.portfolio_id,
                "OrganizationNode": node_param,
                "ShareTagOptions": share_tag_options,
                "SharePrincipals": share_principals,
            },
            physical_resource_id=physical_id,
            ignore_error_codes_matching="ResourceNotFoundException",
        )

        delete_call = AwsSdkCall(
            service="ServiceCatalog",
            action="deletePortfolioShare",
            parameters={
                "PortfolioId": portfolio.portfolio_id,
                "OrganizationNode": node_param,
            },
            ignore_error_codes_matching="ResourceNotFoundException",
        )

        AwsCustomResource(
            self,
            "PortfolioOrgShareCR",
            on_create=create_call,
            on_update=update_call,
            on_delete=delete_call,
            policy=AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=[
                        "servicecatalog:CreatePortfolioShare",
                        "servicecatalog:UpdatePortfolioShare",
                        "servicecatalog:DeletePortfolioShare",
                        "servicecatalog:DescribePortfolioShares",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=[
                        "organizations:ListDelegatedAdministrators",
                        "organizations:ListParents",
                        "organizations:ListChildren",
                    ],
                    resources=["*"],
                ),
            ]),
            timeout=Duration.seconds(15),
        )
