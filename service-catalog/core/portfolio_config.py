"""Portfolio configuration loader for ResearchStack Service Catalog.

Loads portfolio TOML configs with inline product definitions.
Each product declares a template path and the managed policies its launch role needs.
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging

from core.framework_config import FrameworkConfigError, get_framework_config

logger = logging.getLogger(__name__)


@dataclass
class CustomPolicyStatement:
    """An inline IAM policy statement for a launch role."""
    actions: List[str]
    resources: List[str]
    effect: str = "Allow"


@dataclass
class ProductConfig:
    """A product within a portfolio."""
    name: str  # machine-friendly identifier (used for IAM roles, StackSets)
    template: str  # relative path to CloudFormation template
    display_name: str = ""  # human-friendly name shown in Service Catalog console
    description: str = ""  # product description shown in Service Catalog console
    launch_role_policies: List[str] = field(default_factory=list)
    custom_policy: List[CustomPolicyStatement] = field(default_factory=list)


@dataclass
class PortfolioConfig:
    """Parsed portfolio configuration."""
    name: str
    display_name: str
    description: str
    provider_name: str = "ResearchStack on AWS"
    support_email: str = ""
    support_url: str = ""
    support_description: str = ""
    distributor: str = ""
    products: List[ProductConfig] = field(default_factory=list)
    target_ous: List[str] = field(default_factory=list)
    access_principals: List[str] = field(default_factory=list)  # wildcard ARNs for IAM_PATTERN
    share_tag_options: bool = True
    share_principals: bool = True


class PortfolioConfigLoader:
    """Loads portfolio TOML files from the portfolios/ directory."""

    def __init__(self, portfolios_dir: Optional[Path] = None):
        if portfolios_dir is None:
            portfolios_dir = Path(__file__).parent.parent / "portfolios"
        self.portfolios_dir = portfolios_dir
        self.framework_config = get_framework_config()

    def list_portfolios(self) -> List[str]:
        """Return portfolio names (TOML filenames without extension)."""
        if not self.portfolios_dir.exists():
            logger.warning("Portfolios directory not found: %s", self.portfolios_dir)
            return []
        return sorted(
            p.stem for p in self.portfolios_dir.glob("*.toml")
            if not p.name.startswith(("_", "."))
        )

    def load_portfolio_config(self, portfolio_name: str) -> PortfolioConfig:
        """Load and validate a portfolio TOML config."""
        config_file = self.portfolios_dir / f"{portfolio_name}.toml"
        if not config_file.exists():
            raise FrameworkConfigError(
                f"Portfolio config not found: {config_file}",
                f"Create {portfolio_name}.toml in the portfolios/ directory",
            )

        try:
            with open(config_file, "rb") as f:
                raw = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise FrameworkConfigError(
                f"Invalid TOML in {portfolio_name}.toml",
                "Check TOML syntax",
                str(e),
            )

        ps = raw.get("portfolio", {})
        if not ps:
            raise FrameworkConfigError(
                f"Missing [portfolio] section in {portfolio_name}.toml",
                "Add a [portfolio] section with name, display_name, and products",
            )

        # Parse inline products
        products = []
        for p in ps.get("products", []):
            if not p.get("name") or not p.get("template"):
                raise FrameworkConfigError(
                    f"Product in {portfolio_name}.toml missing 'name' or 'template'",
                    "Each [[portfolio.products]] needs name and template fields",
                )
            products.append(ProductConfig(
                name=p["name"],
                template=p["template"],
                display_name=p.get("display_name", p["name"].replace("-", " ").title()),
                description=p.get("description", ""),
                launch_role_policies=p.get("launch_role_policies", []),
                custom_policy=[
                    CustomPolicyStatement(
                        actions=stmt["actions"],
                        resources=stmt["resources"],
                        effect=stmt.get("effect", "Allow"),
                    )
                    for stmt in p.get("custom_policy", [])
                ],
            ))

        config = PortfolioConfig(
            name=ps.get("name", portfolio_name),
            display_name=ps.get("display_name", portfolio_name.replace("-", " ").title()),
            description=ps.get("description", ""),
            provider_name=ps.get("provider_name", "ResearchStack on AWS"),
            support_email=ps.get("support_email", ""),
            support_url=ps.get("support_url", ""),
            support_description=ps.get("support_description", ""),
            distributor=ps.get("distributor", ""),
            products=products,
            target_ous=ps.get("share_target_ous", []),
            access_principals=ps.get("access_principals", []),
            share_tag_options=ps.get("share_tag_options", True),
            share_principals=ps.get("share_principals", True),
        )

        self._validate(config, portfolio_name)
        return config

    def _validate(self, config: PortfolioConfig, portfolio_name: str) -> None:
        if not config.name:
            raise FrameworkConfigError(f"Portfolio name is required in {portfolio_name}.toml", "Set portfolio.name")
        if not config.display_name:
            raise FrameworkConfigError(f"Display name required in {portfolio_name}.toml", "Set portfolio.display_name")

        # Validate target OUs are in framework config
        available = set(self.framework_config.available_ous)
        invalid = set(config.target_ous) - available
        if invalid:
            raise FrameworkConfigError(
                f"Invalid target OUs in {portfolio_name}: {', '.join(invalid)}",
                f"Use OUs from framework_config.yaml available_ous: {', '.join(available)}",
            )

        if not config.products:
            logger.warning("Portfolio '%s' has no products configured", portfolio_name)
