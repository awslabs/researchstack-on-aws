# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Framework configuration loader for ResearchStack Service Catalog.

Loads deployment settings, available OUs, and tagging config from framework_config.yaml.
Validates required fields and formats before CDK synthesis.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class FrameworkConfigError(Exception):
    """Configuration error with actionable suggestion."""

    def __init__(self, message: str, suggestion: str, technical_details: str = ""):
        self.message = message
        self.suggestion = suggestion
        self.technical_details = technical_details
        super().__init__(f"{message} — {suggestion}")


@dataclass
class DeploymentConfig:
    hub_account: str = ""
    hub_region: str = ""
    organization_id: str = ""
    default_env_name: str = "dev"


@dataclass
class TaggingConfig:
    required_tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class FrameworkConfig:
    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)
    available_ous: List[str] = field(default_factory=list)
    tagging: TaggingConfig = field(default_factory=TaggingConfig)


class FrameworkConfigLoader:
    """Loads and validates framework_config.yaml."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "framework_config.yaml"
        self.config_path = config_path
        self._config: Optional[FrameworkConfig] = None

    def load_config(self) -> FrameworkConfig:
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            raise FrameworkConfigError(
                f"Config file not found: {self.config_path}",
                "Create framework_config.yaml in the service-catalog/ directory",
            )

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise FrameworkConfigError("Invalid YAML syntax", "Check framework_config.yaml syntax", str(e))

        dep = raw.get("deployment", {})
        tag = raw.get("tagging", {})

        self._config = FrameworkConfig(
            deployment=DeploymentConfig(
                hub_account=dep.get("hub_account", ""),
                hub_region=dep.get("hub_region", ""),
                organization_id=dep.get("organization_id", ""),
                default_env_name=dep.get("default_env_name", "dev"),
            ),
            available_ous=raw.get("available_ous", []),
            tagging=TaggingConfig(required_tags=tag.get("required_tags", {})),
        )

        self._validate(self._config)
        return self._config

    def _validate(self, config: FrameworkConfig) -> None:
        d = config.deployment
        if not d.hub_account or not re.match(r"^\d{12}$", d.hub_account):
            raise FrameworkConfigError(
                f"Invalid hub_account: '{d.hub_account}'",
                "Set deployment.hub_account to a 12-digit AWS account ID",
            )
        if not d.hub_region or not re.match(r"^[a-z]{2}-[a-z]+-\d+$", d.hub_region):
            raise FrameworkConfigError(
                f"Invalid hub_region: '{d.hub_region}'",
                "Use standard AWS region format like 'us-east-1'",
            )
        if not d.organization_id or not re.match(r"^o-[a-z0-9]{10,32}$", d.organization_id):
            raise FrameworkConfigError(
                f"Invalid organization_id: '{d.organization_id}'",
                "Set deployment.organization_id to your AWS Organization ID (o-xxxxxxxxxx)",
            )
        from utils.resource_naming import NameValidator
        for ou_id in config.available_ous:
            ok, reason = NameValidator.validate_ou_id(ou_id)
            if not ok:
                raise FrameworkConfigError(f"Invalid OU ID: {ou_id}", reason)


# Module-level singleton
_loader: Optional[FrameworkConfigLoader] = None


def get_framework_config(config_path: Optional[Path] = None) -> FrameworkConfig:
    global _loader
    if _loader is None or config_path is not None:
        _loader = FrameworkConfigLoader(config_path)
    return _loader.load_config()
