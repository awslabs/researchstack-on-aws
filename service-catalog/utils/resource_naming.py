"""Standardized resource naming for CloudFormation stacks and SC launch roles."""

import re
from typing import Optional, Tuple

from utils.config import GlobalConfig


class NameValidator:
    """Validates AWS Organizations IDs."""

    @classmethod
    def validate_ou_id(cls, ou_id: str) -> Tuple[bool, str]:
        if not ou_id:
            return False, "OU ID cannot be empty"
        if not re.match(r"^ou-[a-z0-9]+-[a-z0-9]+$", ou_id):
            return False, "OU ID must be in format ou-xxxxxxxxx-yyyyyyyyy"
        return True, ""

    @classmethod
    def validate_organization_id(cls, org_id: str) -> Tuple[bool, str]:
        if not org_id:
            return False, "Organization ID cannot be empty"
        if not re.match(r"^o-[a-z0-9]{10,32}$", org_id):
            return False, "Organization ID must be in format o-example123456"
        return True, ""


class ResourceNaming:
    """Basic name sanitization for AWS resources."""

    @staticmethod
    def sanitize_name(name: str) -> str:
        if not name:
            return "default"
        sanitized = re.sub(r"[^a-zA-Z0-9\-]", "-", name).lower().strip("-")
        if sanitized and not sanitized[0].isalnum():
            sanitized = "r" + sanitized
        return sanitized or "default"


class ServiceCatalogRoleNaming:
    """Naming for SC launch constraint roles: {slug}-{env}-{portfolio}-{product}-lc"""

    @staticmethod
    def _get_standard_name(
        product_name: str,
        portfolio_name: str,
        project_slug: Optional[str] = None,
        env_name: Optional[str] = None,
    ) -> str:
        project_slug = (project_slug or GlobalConfig.get_project_slug()).replace("_", "-").lower()
        env_name = (env_name or GlobalConfig.get_env_name()).replace("_", "-").lower()
        product = product_name.replace("_", "-").lower()
        portfolio = portfolio_name.replace("_", "-").lower()
        return f"{project_slug}-{env_name}-{portfolio}-{product}-lc"

    @classmethod
    def get_launch_role_name(cls, product_name: str, portfolio_name: str, **kwargs) -> str:
        return ResourceNaming.sanitize_name(cls._get_standard_name(product_name, portfolio_name, **kwargs))

    @classmethod
    def get_stackset_name(cls, product_name: str, portfolio_name: str, **kwargs) -> str:
        return cls._get_standard_name(product_name, portfolio_name, **kwargs)

    @staticmethod
    def validate_name_components(product_name: str, portfolio_name: str, **kwargs) -> Tuple[bool, str]:
        if not product_name:
            return False, "product_name cannot be empty"
        if not portfolio_name:
            return False, "portfolio_name cannot be empty"
        pattern = re.compile(r"^[a-zA-Z0-9\-_]+$")
        for label, val in [("product_name", product_name), ("portfolio_name", portfolio_name)]:
            if not pattern.match(val):
                return False, f"{label} can only contain letters, numbers, hyphens, and underscores"
        return True, ""


class CloudFormationStackNaming:
    """Stack naming: {slug}-{env}-{component}-stack"""

    @staticmethod
    def get_stack_name(
        component: str,
        project_slug: Optional[str] = None,
        env_name: Optional[str] = None,
    ) -> str:
        project_slug = (project_slug or GlobalConfig.get_project_slug()).replace("_", "-").lower()
        env_name = (env_name or GlobalConfig.get_env_name()).replace("_", "-").lower()
        component = component.replace("_", "-").lower().strip()
        return f"{project_slug}-{env_name}-{component}-stack"
