"""Tests for resource_naming.py — naming conventions and validation."""

import pytest
from unittest.mock import patch

from utils.resource_naming import (
    NameValidator,
    ResourceNaming,
    ServiceCatalogRoleNaming,
    CloudFormationStackNaming,
)


class TestNameValidator:

    def test_valid_ou_id(self):
        ok, _ = NameValidator.validate_ou_id("ou-abcd-12345678")
        assert ok

    def test_empty_ou_id(self):
        ok, reason = NameValidator.validate_ou_id("")
        assert not ok
        assert "empty" in reason.lower()

    def test_invalid_ou_format(self):
        ok, reason = NameValidator.validate_ou_id("not-an-ou")
        assert not ok

    def test_valid_org_id(self):
        ok, _ = NameValidator.validate_organization_id("o-abcdefghij")
        assert ok

    def test_empty_org_id(self):
        ok, _ = NameValidator.validate_organization_id("")
        assert not ok

    def test_invalid_org_format(self):
        ok, _ = NameValidator.validate_organization_id("bad-org")
        assert not ok


class TestResourceNaming:

    def test_sanitize_basic(self):
        assert ResourceNaming.sanitize_name("my-resource") == "my-resource"

    def test_sanitize_special_chars(self):
        result = ResourceNaming.sanitize_name("My_Cool Stack!")
        assert result == "my-cool-stack"  # special chars → hyphens, trailing hyphen stripped

    def test_sanitize_uppercase(self):
        assert ResourceNaming.sanitize_name("MyResource") == "myresource"

    def test_sanitize_empty(self):
        assert ResourceNaming.sanitize_name("") == "default"

    def test_sanitize_none_like(self):
        assert ResourceNaming.sanitize_name("") == "default"


class TestServiceCatalogRoleNaming:

    def test_launch_role_name(self):
        name = ServiceCatalogRoleNaming.get_launch_role_name(
            product_name="s3-bucket",
            portfolio_name="research",
            project_slug="rs",
            env_name="dev",
        )
        assert name == "rs-dev-research-s3-bucket-lc"

    def test_stackset_name(self):
        name = ServiceCatalogRoleNaming.get_stackset_name(
            product_name="s3-bucket",
            portfolio_name="research",
            project_slug="rs",
            env_name="dev",
        )
        assert name == "rs-dev-research-s3-bucket-lc"

    def test_validate_valid_components(self):
        ok, _ = ServiceCatalogRoleNaming.validate_name_components(
            product_name="s3-bucket", portfolio_name="research"
        )
        assert ok

    def test_validate_empty_product(self):
        ok, reason = ServiceCatalogRoleNaming.validate_name_components(
            product_name="", portfolio_name="research"
        )
        assert not ok
        assert "product_name" in reason

    def test_validate_empty_portfolio(self):
        ok, reason = ServiceCatalogRoleNaming.validate_name_components(
            product_name="s3-bucket", portfolio_name=""
        )
        assert not ok
        assert "portfolio_name" in reason

    def test_validate_special_chars_rejected(self):
        ok, _ = ServiceCatalogRoleNaming.validate_name_components(
            product_name="s3 bucket!", portfolio_name="research"
        )
        assert not ok


class TestCloudFormationStackNaming:

    def test_stack_name(self):
        name = CloudFormationStackNaming.get_stack_name(
            component="assets", project_slug="rs", env_name="dev"
        )
        assert name == "rs-dev-assets-stack"

    def test_stack_name_with_underscores(self):
        name = CloudFormationStackNaming.get_stack_name(
            component="my_component", project_slug="rs", env_name="dev"
        )
        assert name == "rs-dev-my-component-stack"

    def test_stack_name_uses_global_defaults(self):
        with patch("utils.resource_naming.GlobalConfig.get_project_slug", return_value="test"):
            with patch("utils.resource_naming.GlobalConfig.get_env_name", return_value="prod"):
                name = CloudFormationStackNaming.get_stack_name("assets")
                assert name == "test-prod-assets-stack"


class TestLaunchRoleStacksetProps:
    """Test LaunchRoleStacksetProps validation (lives in sc_constructs but uses naming)."""

    def test_valid_props(self):
        from sc_constructs.launch_role_stackset_template import LaunchRoleStacksetProps
        props = LaunchRoleStacksetProps(
            product_name="s3-bucket",
            portfolio_name="research",
            managed_policy_names=["AmazonS3FullAccess"],
        )
        assert props.product_name == "s3-bucket"

    def test_invalid_product_name_raises(self):
        from sc_constructs.launch_role_stackset_template import LaunchRoleStacksetProps
        with pytest.raises(ValueError, match="Invalid stackset name"):
            LaunchRoleStacksetProps(
                product_name="bad name!",
                portfolio_name="research",
            )

    def test_empty_product_name_raises(self):
        from sc_constructs.launch_role_stackset_template import LaunchRoleStacksetProps
        with pytest.raises(ValueError, match="Invalid stackset name"):
            LaunchRoleStacksetProps(
                product_name="",
                portfolio_name="research",
            )
