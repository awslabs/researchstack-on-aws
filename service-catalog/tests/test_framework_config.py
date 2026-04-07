"""Tests for framework_config.py — config loading and validation."""

import pytest
from pathlib import Path
from unittest.mock import patch

from core.framework_config import (
    FrameworkConfigError,
    FrameworkConfigLoader,
    FrameworkConfig,
    DeploymentConfig,
)


class TestFrameworkConfigLoading:
    """Test that valid configs load correctly."""

    def test_valid_config_loads(self, valid_framework_config):
        loader = FrameworkConfigLoader(valid_framework_config)
        config = loader.load_config()

        assert config.deployment.hub_account == "123456789012"
        assert config.deployment.hub_region == "us-east-1"
        assert config.deployment.organization_id == "o-abc123def456"
        assert config.deployment.default_env_name == "test"
        assert "ou-abcd-12345678" in config.available_ous
        assert config.tagging.required_tags["Project"] == "TestProject"

    def test_config_is_cached(self, valid_framework_config):
        loader = FrameworkConfigLoader(valid_framework_config)
        config1 = loader.load_config()
        config2 = loader.load_config()
        assert config1 is config2

    def test_default_env_name(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "deployment:\n"
            '  hub_account: "111222333444"\n'
            '  hub_region: "us-west-2"\n'
            '  organization_id: "o-abcdefghij"\n'
            "available_ous: []\n"
        )
        loader = FrameworkConfigLoader(cfg)
        config = loader.load_config()
        assert config.deployment.default_env_name == "dev"


class TestFrameworkConfigValidation:
    """Test that invalid configs raise FrameworkConfigError with helpful messages."""

    def test_missing_file_raises(self, tmp_path):
        loader = FrameworkConfigLoader(tmp_path / "nonexistent.yaml")
        with pytest.raises(FrameworkConfigError, match="not found"):
            loader.load_config()

    def test_invalid_yaml_raises(self, tmp_path):
        cfg = tmp_path / "bad.yaml"
        cfg.write_text(": invalid: yaml: {{")
        loader = FrameworkConfigLoader(cfg)
        with pytest.raises(FrameworkConfigError, match="Invalid YAML"):
            loader.load_config()

    def test_invalid_account_id_raises(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "deployment:\n"
            '  hub_account: "short"\n'
            '  hub_region: "us-east-1"\n'
            '  organization_id: "o-abcdefghij"\n'
            "available_ous: []\n"
        )
        loader = FrameworkConfigLoader(cfg)
        with pytest.raises(FrameworkConfigError, match="Invalid hub_account"):
            loader.load_config()

    def test_invalid_region_raises(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "deployment:\n"
            '  hub_account: "123456789012"\n'
            '  hub_region: "not-a-region"\n'
            '  organization_id: "o-abcdefghij"\n'
            "available_ous: []\n"
        )
        loader = FrameworkConfigLoader(cfg)
        with pytest.raises(FrameworkConfigError, match="Invalid hub_region"):
            loader.load_config()

    def test_invalid_org_id_raises(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "deployment:\n"
            '  hub_account: "123456789012"\n'
            '  hub_region: "us-east-1"\n'
            '  organization_id: "bad-org"\n'
            "available_ous: []\n"
        )
        loader = FrameworkConfigLoader(cfg)
        with pytest.raises(FrameworkConfigError, match="Invalid organization_id"):
            loader.load_config()

    def test_invalid_ou_id_raises(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "deployment:\n"
            '  hub_account: "123456789012"\n'
            '  hub_region: "us-east-1"\n'
            '  organization_id: "o-abcdefghij"\n'
            "available_ous:\n"
            '  - "not-an-ou"\n'
        )
        loader = FrameworkConfigLoader(cfg)
        with pytest.raises(FrameworkConfigError, match="Invalid OU ID"):
            loader.load_config()

    def test_empty_file_uses_defaults(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("")
        loader = FrameworkConfigLoader(cfg)
        # Empty file means empty deployment config, which fails validation
        with pytest.raises(FrameworkConfigError, match="Invalid hub_account"):
            loader.load_config()

    def test_error_has_suggestion(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "deployment:\n"
            '  hub_account: "bad"\n'
            '  hub_region: "us-east-1"\n'
            '  organization_id: "o-abcdefghij"\n'
        )
        loader = FrameworkConfigLoader(cfg)
        with pytest.raises(FrameworkConfigError) as exc_info:
            loader.load_config()
        assert "12-digit" in exc_info.value.suggestion


class TestGetFrameworkConfigSingleton:
    """Test the module-level get_framework_config() function."""

    def test_singleton_returns_config(self, valid_framework_config):
        from core.framework_config import get_framework_config, _loader
        # Reset the module singleton
        import core.framework_config as mod
        mod._loader = None

        config = get_framework_config(valid_framework_config)
        assert config.deployment.hub_account == "123456789012"

        # Second call without path returns cached
        config2 = get_framework_config()
        assert config2 is config

        # Cleanup
        mod._loader = None
