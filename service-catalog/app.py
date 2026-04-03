"""ResearchStack on AWS - Service Catalog deployment entrypoint.

Reads framework_config.yaml and portfolio TOML configs, then synthesizes:
  1. AssetsStack — S3 bucket for template artifacts
  2. PortfolioStack (per portfolio) — SC portfolio, products, launch roles, StackSets
"""

import logging
import sys

from aws_cdk import App, Environment

from core.framework_config import FrameworkConfigError, get_framework_config
from core.portfolio_config import PortfolioConfigLoader
from stacks.assets_stack import AssetsStack
from stacks.portfolio_stack import PortfolioStack
from utils.config import GlobalConfig
from utils.resource_naming import CloudFormationStackNaming
from utils.tagging import apply_standard_tags

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("arc-sc")


def main():
    try:
        config = get_framework_config()
    except FrameworkConfigError as e:
        logger.error("%s", e.message)
        logger.error("  → %s", e.suggestion)
        sys.exit(1)

    env_name = config.deployment.default_env_name
    GlobalConfig.set_env_name(env_name)

    hub_env = Environment(
        account=config.deployment.hub_account,
        region=config.deployment.hub_region,
    )

    app = App()

    # Override project slug from CDK context if provided
    slug = app.node.try_get_context("project_slug")
    if slug:
        GlobalConfig.set_project_slug(slug)

    # 1. Assets stack (S3 bucket for SC template artifacts)
    assets_stack_name = CloudFormationStackNaming.get_stack_name("assets")
    assets_stack = AssetsStack(
        app,
        assets_stack_name,
        stack_name=assets_stack_name,
        organization_id=config.deployment.organization_id,
        env=hub_env,
    )

    # 2. Portfolio stacks
    loader = PortfolioConfigLoader()
    portfolios = loader.list_portfolios()

    if not portfolios:
        logger.warning("No portfolio configs found in portfolios/ — deploying assets stack only")

    for portfolio_name in portfolios:
        try:
            portfolio_config = loader.load_portfolio_config(portfolio_name)
            stack_name = CloudFormationStackNaming.get_stack_name(f"{portfolio_name}-portfolio")

            portfolio_stack = PortfolioStack(
                app,
                stack_name,
                stack_name=stack_name,
                portfolio_config=portfolio_config,
                asset_bucket=assets_stack.assets_bucket,
                env=hub_env,
            )
            portfolio_stack.node.add_dependency(assets_stack)

            logger.info("Portfolio ready: %s", portfolio_name)

        except FrameworkConfigError as e:
            logger.error("Failed to load portfolio '%s': %s", portfolio_name, e.message)
            sys.exit(1)

    # Apply standard tags to all stacks
    apply_standard_tags(app, env_name)

    app.synth()
    logger.info("Synthesis complete")


if __name__ == "__main__":
    main()
