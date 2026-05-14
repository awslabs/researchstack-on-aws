# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for utils/config.py — GlobalConfig singleton."""

from utils.config import GlobalConfig


class TestGlobalConfig:

    def setup_method(self):
        """Reset to defaults before each test."""
        GlobalConfig.env_name = "dev"
        GlobalConfig.project_slug = "rs"

    def test_default_env_name(self):
        assert GlobalConfig.get_env_name() == "dev"

    def test_set_env_name(self):
        GlobalConfig.set_env_name("prod")
        assert GlobalConfig.get_env_name() == "prod"

    def test_default_project_slug(self):
        assert GlobalConfig.get_project_slug() == "rs"

    def test_set_project_slug(self):
        GlobalConfig.set_project_slug("myorg")
        assert GlobalConfig.get_project_slug() == "myorg"

    def test_env_name_from_environment_variable(self, monkeypatch):
        monkeypatch.setenv("ENV_NAME", "staging")
        assert GlobalConfig.get_env_name() == "staging"

    def test_env_name_class_var_ignored_when_env_set(self, monkeypatch):
        GlobalConfig.set_env_name("dev")
        monkeypatch.setenv("ENV_NAME", "prod")
        assert GlobalConfig.get_env_name() == "prod"
