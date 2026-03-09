"""StackSet template that deploys a launch role into target accounts."""

from typing import List, Optional

from aws_cdk import aws_iam as iam
from constructs import Construct

from sc_constructs.base_stackset_template import BaseStacksetTemplate
from sc_constructs.launch_role import LaunchRoleConstruct
from utils.resource_naming import ServiceCatalogRoleNaming


class LaunchRoleStacksetProps:
    """Properties for the launch role stackset template."""

    def __init__(
        self,
        product_name: str,
        portfolio_name: str,
        managed_policy_names: Optional[List[str]] = None,
    ):
        ok, reason = ServiceCatalogRoleNaming.validate_name_components(
            product_name=product_name,
            portfolio_name=portfolio_name,
        )
        if not ok:
            raise ValueError(f"Invalid stackset name components: {reason}")

        self.product_name = product_name
        self.portfolio_name = portfolio_name
        self.managed_policy_names = managed_policy_names or []


class LaunchRoleStacksetTemplate(BaseStacksetTemplate):
    """Synthesizes a CFN template that creates a launch role in target accounts."""

    def __init__(self, scope: Construct, id: str, props: LaunchRoleStacksetProps, **kwargs) -> None:
        props_dict = props if isinstance(props, dict) else props.__dict__
        super().__init__(scope, id, props_dict, **kwargs)

        LaunchRoleConstruct(
            self,
            "LaunchRoleConstruct",
            product_name=self.props["product_name"],
            portfolio_name=self.props["portfolio_name"],
            managed_policy_names=self.props.get("managed_policy_names", []),
        )
