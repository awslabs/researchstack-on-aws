"""Tests for utils/config.py — GlobalConfig singleton."""

from utils.config import GlobalConfig


class TestGlobalConfig:

    def setup_method(self):
        """Reset to defaults before each test."""
        GlobalConfig.env_name = "dev"
        GlobalConfig.project_slug = "arc"

    def test_default_env_name(self):
        assert GlobalConfig.get_env_name() == "dev"

    def test_set_env_name(self):
        GlobalConfig.set_env_name("prod")
        assert GlobalConfig.get_env_name() == "prod"

    def test_default_project_slug(self):
        assert GlobalConfig.get_project_slug() == "arc"

    def test_set_project_slug(self):
        GlobalConfig.set_project_slug("myorg")
        assert GlobalConfig.get_project_slug() == "myorg"
