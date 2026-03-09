"""Service Catalog portfolio stack.

Creates a portfolio, adds products (from CloudFormation template files),
shares with OUs, and deploys per-product launch roles via StackSets.
"""

import logging
from pathlib import Path

from aws_cdk import Stack
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_servicecatalog as sc
from constructs import Construct

from sc_constructs.launch_role import LaunchRoleConstruct
from sc_constructs.launch_role_stackset_template import LaunchRoleStacksetProps
from sc_constructs.portfolio_share import OrganizationNodeType, PortfolioShare
from sc_constructs.stackset_factory import StacksetFactory
from core.portfolio_config import PortfolioConfig, ProductConfig
from utils.resource_naming import ServiceCatalogRoleNaming

logger = logging.getLogger(__name__)


class PortfolioStack(Stack):
    """Deploys a single SC portfolio with its products and launch roles."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        portfolio_config: PortfolioConfig,
        asset_bucket: s3.IBucket,
        **kwargs,
    ) -> None:
        description = (portfolio_config.description or "")[:1024]
        super().__init__(scope, construct_id, description=description, **kwargs)

        self.config = portfolio_config

        # Create the portfolio
        self.portfolio = sc.Portfolio(
            self,
            "Portfolio",
            display_name=portfolio_config.display_name,
            provider_name=portfolio_config.provider_name,
            description=portfolio_config.description,
        )

        # Share with OUs
        for ou_id in portfolio_config.target_ous:
            logger.info("Sharing portfolio with OU: %s", ou_id)
            PortfolioShare(
                self,
                f"Share-{ou_id}",
                portfolio=self.portfolio,
                organization_node_type=OrganizationNodeType.ORGANIZATIONAL_UNIT,
                organization_node_value=ou_id,
                share_tag_options=portfolio_config.share_tag_options,
                share_principals=portfolio_config.share_principals,
            )

        # StackSet factory for deploying launch roles to target accounts
        self.stackset_factory = StacksetFactory(self, "StacksetFactory")

        # Add each product
        for product_cfg in portfolio_config.products:
            self._add_product(product_cfg, asset_bucket)

    def _add_product(self, product_cfg: ProductConfig, asset_bucket: s3.IBucket) -> None:
        """Add a product to the portfolio with its launch role."""
        template_path = (Path(__file__).parent.parent / product_cfg.template).resolve()
        if not template_path.exists():
            raise FileNotFoundError(
                f"Template not found for product '{product_cfg.name}': {template_path}"
            )

        # Create the SC product from the CloudFormation template file
        product = sc.CloudFormationProduct(
            self,
            f"Product-{product_cfg.name}",
            product_name=product_cfg.name,
            owner=self.config.provider_name,
            product_versions=[
                sc.CloudFormationProductVersion(
                    product_version_name="v1",
                    cloud_formation_template=sc.CloudFormationTemplate.from_asset(
                        str(template_path)
                    ),
                )
            ],
        )

        # Associate product with portfolio
        self.portfolio.add_product(product)

        # Create launch role in hub account
        launch_role_construct = LaunchRoleConstruct(
            self,
            f"LaunchRole-{product_cfg.name}",
            product_name=product_cfg.name,
            portfolio_name=self.config.name,
            managed_policy_names=product_cfg.launch_role_policies,
        )

        # Add launch constraint so SC uses this role
        self.portfolio.set_launch_role(product, launch_role_construct.role)

        # Deploy launch role to target accounts via StackSet
        if self.config.target_ous:
            stackset_name = ServiceCatalogRoleNaming.get_stackset_name(
                product_name=product_cfg.name,
                portfolio_name=self.config.name,
            )
            self.stackset_factory.create_launch_role_stackset(
                stack_name=stackset_name,
                props=LaunchRoleStacksetProps(
                    product_name=product_cfg.name,
                    portfolio_name=self.config.name,
                    managed_policy_names=product_cfg.launch_role_policies,
                ),
                target_regions=[Stack.of(self).region],
                target_ou_ids=self.config.target_ous,
                capabilities=["CAPABILITY_NAMED_IAM"],
            )

        logger.info("Added product '%s' to portfolio '%s'", product_cfg.name, self.config.name)
