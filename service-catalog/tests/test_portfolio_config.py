"""Tests for portfolio_config.py — TOML loading and validation."""

import pytest
from pathlib import Path
from unittest.mock import patch

from core.framework_config import FrameworkConfigError
from core.portfolio_config import PortfolioConfigLoader, PortfolioConfig, ProductConfig


@pytest.fixture
def mock_framework_config(valid_framework_config):
    """Patch get_framework_config to use our test fixture."""
    from core.framework_config import FrameworkConfigLoader as FCL

    loader = FCL(valid_framework_config)
    config = loader.load_config()
    with patch("core.portfolio_config.get_framework_config", return_value=config):
        yield config


class TestPortfolioConfigLoading:
    """Test that valid portfolio TOMLs load correctly."""

    def test_valid_portfolio_loads(self, valid_portfolio_dir, mock_framework_config):
        loader = PortfolioConfigLoader(valid_portfolio_dir)
        config = loader.load_portfolio_config("test-portfolio")

        assert config.name == "test-portfolio"
        assert config.display_name == "Test Portfolio"
        assert config.provider_name == "Test Provider"
        assert len(config.products) == 1
        assert config.products[0].name == "test-product"
        assert config.products[0].template == "../templates/storage/s3-research-bucket.yaml"
        assert "AmazonS3FullAccess" in config.products[0].launch_role_policies

    def test_list_portfolios(self, valid_portfolio_dir, mock_framework_config):
        loader = PortfolioConfigLoader(valid_portfolio_dir)
        portfolios = loader.list_portfolios()
        assert "test-portfolio" in portfolios

    def test_list_portfolios_empty_dir(self, tmp_path, mock_framework_config):
        loader = PortfolioConfigLoader(tmp_path)
        assert loader.list_portfolios() == []

    def test_list_portfolios_missing_dir(self, tmp_path, mock_framework_config):
        loader = PortfolioConfigLoader(tmp_path / "nonexistent")
        assert loader.list_portfolios() == []

    def test_target_ous_parsed(self, valid_portfolio_dir, mock_framework_config):
        loader = PortfolioConfigLoader(valid_portfolio_dir)
        config = loader.load_portfolio_config("test-portfolio")
        assert "ou-abcd-12345678" in config.target_ous

    def test_share_settings_parsed(self, valid_portfolio_dir, mock_framework_config):
        loader = PortfolioConfigLoader(valid_portfolio_dir)
        config = loader.load_portfolio_config("test-portfolio")
        assert config.share_tag_options is True
        assert config.share_principals is True


class TestPortfolioConfigValidation:
    """Test that invalid portfolio configs raise errors."""

    def test_missing_toml_raises(self, tmp_path, mock_framework_config):
        loader = PortfolioConfigLoader(tmp_path)
        with pytest.raises(FrameworkConfigError, match="not found"):
            loader.load_portfolio_config("nonexistent")

    def test_invalid_toml_raises(self, tmp_path, mock_framework_config):
        (tmp_path / "bad.toml").write_text("[[invalid toml")
        loader = PortfolioConfigLoader(tmp_path)
        with pytest.raises(FrameworkConfigError, match="Invalid TOML"):
            loader.load_portfolio_config("bad")

    def test_missing_portfolio_section_raises(self, tmp_path, mock_framework_config):
        (tmp_path / "empty.toml").write_text('[other]\nkey = "value"\n')
        loader = PortfolioConfigLoader(tmp_path)
        with pytest.raises(FrameworkConfigError, match="Missing.*portfolio.*section"):
            loader.load_portfolio_config("empty")

    def test_product_missing_name_raises(self, tmp_path, mock_framework_config):
        (tmp_path / "bad-product.toml").write_text(
            '[portfolio]\nname = "test"\ndisplay_name = "Test"\n'
            "share_target_ous = []\n\n"
            "[[portfolio.products]]\n"
            'template = "../templates/storage/s3-research-bucket.yaml"\n'
        )
        loader = PortfolioConfigLoader(tmp_path)
        with pytest.raises(FrameworkConfigError, match="missing.*name.*template"):
            loader.load_portfolio_config("bad-product")

    def test_product_missing_template_raises(self, tmp_path, mock_framework_config):
        (tmp_path / "bad-product2.toml").write_text(
            '[portfolio]\nname = "test"\ndisplay_name = "Test"\n'
            "share_target_ous = []\n\n"
            "[[portfolio.products]]\n"
            'name = "my-product"\n'
        )
        loader = PortfolioConfigLoader(tmp_path)
        with pytest.raises(FrameworkConfigError, match="missing.*name.*template"):
            loader.load_portfolio_config("bad-product2")

    def test_invalid_ou_raises(self, tmp_path, mock_framework_config):
        (tmp_path / "bad-ou.toml").write_text(
            '[portfolio]\nname = "test"\ndisplay_name = "Test"\n'
            'share_target_ous = ["ou-xxxx-99999999"]\n'
        )
        loader = PortfolioConfigLoader(tmp_path)
        with pytest.raises(FrameworkConfigError, match="Invalid target OUs"):
            loader.load_portfolio_config("bad-ou")
