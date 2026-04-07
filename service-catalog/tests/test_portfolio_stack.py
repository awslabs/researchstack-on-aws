"""Tests for portfolio_stack.py — SC portfolio, products, launch roles, StackSets."""

import pytest
from aws_cdk import App, Environment
from aws_cdk import aws_s3 as s3
from aws_cdk.assertions import Template, Match

from stacks.assets_stack import AssetsStack
from stacks.portfolio_stack import PortfolioStack
from core.portfolio_config import PortfolioConfig, ProductConfig
from utils.config import GlobalConfig


@pytest.fixture(autouse=True)
def reset_globals():
    GlobalConfig.env_name = "test"
    GlobalConfig.project_slug = "rs"


def _make_portfolio_config(products=None, target_ous=None, access_principals=None):
    """Helper to create a minimal PortfolioConfig for testing."""
    if products is None:
        products = [
            ProductConfig(
                name="s3-research-bucket",
                template="../templates/storage/s3-research-bucket.yaml",
                display_name="Storage Bucket",
                description="Test S3 product",
                launch_role_policies=["AmazonS3FullAccess"],
            ),
        ]
    return PortfolioConfig(
        name="test-portfolio",
        display_name="Test Portfolio",
        description="Portfolio for unit tests",
        provider_name="Test Provider",
        products=products,
        target_ous=target_ous or [],
        access_principals=access_principals or [],
        share_tag_options=True,
        share_principals=True,
    )

@pytest.fixture
def portfolio_template():
    """Synth a portfolio stack with one product, no OU sharing."""
    app = App()
    env = Environment(account="123456789012", region="us-east-1")

    assets_stack = AssetsStack(
        app, "Assets",
        organization_id="o-abc123def456",
        env=env,
    )

    config = _make_portfolio_config()
    stack = PortfolioStack(
        app, "TestPortfolio",
        portfolio_config=config,
        asset_bucket=assets_stack.assets_bucket,
        env=env,
    )
    return Template.from_stack(stack)


@pytest.fixture
def portfolio_with_ou_template():
    """Synth a portfolio stack with one product and OU sharing."""
    app = App()
    env = Environment(account="123456789012", region="us-east-1")

    assets_stack = AssetsStack(
        app, "Assets",
        organization_id="o-abc123def456",
        env=env,
    )

    config = _make_portfolio_config(
        target_ous=["ou-abcd-12345678"],
        access_principals=[
            "arn:aws:iam:::role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_TestAccess*",
        ],
    )
    stack = PortfolioStack(
        app, "TestPortfolioOU",
        portfolio_config=config,
        asset_bucket=assets_stack.assets_bucket,
        env=env,
    )
    return Template.from_stack(stack)


class TestPortfolioCreation:

    def test_creates_portfolio(self, portfolio_template):
        portfolio_template.has_resource_properties(
            "AWS::ServiceCatalog::Portfolio",
            {
                "DisplayName": "Test Portfolio",
                "ProviderName": "Test Provider",
            },
        )

    def test_creates_product(self, portfolio_template):
        portfolio_template.has_resource_properties(
            "AWS::ServiceCatalog::CloudFormationProduct",
            {
                "Name": "Storage Bucket",
                "Owner": "Test Provider",
            },
        )


class TestLaunchRoles:

    def test_creates_launch_role(self, portfolio_template):
        portfolio_template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "RoleName": "rs-test-test-portfolio-s3-research-bucket-lc",
                "AssumeRolePolicyDocument": Match.object_like({
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Principal": {"Service": "servicecatalog.amazonaws.com"},
                        }),
                    ]),
                }),
            },
        )

    def test_launch_role_has_declared_policies(self, portfolio_template):
        portfolio_template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "RoleName": "rs-test-test-portfolio-s3-research-bucket-lc",
                "ManagedPolicyArns": Match.array_with([
                    Match.object_like({}),  # At least one managed policy
                ]),
            },
        )


class TestOUSharing:

    def test_creates_portfolio_share_custom_resource(self, portfolio_with_ou_template):
        # PortfolioShare uses AwsCustomResource which creates a AWS::CloudFormation::CustomResource
        portfolio_with_ou_template.has_resource("Custom::AWS", Match.object_like({}))

    def test_creates_principal_association(self, portfolio_with_ou_template):
        portfolio_with_ou_template.has_resource_properties(
            "AWS::ServiceCatalog::PortfolioPrincipalAssociation",
            {
                "PrincipalType": "IAM_PATTERN",
                "PrincipalARN": "arn:aws:iam:::role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_TestAccess*",
            },
        )


class TestStackSets:

    def test_creates_stackset_when_ous_provided(self, portfolio_with_ou_template):
        portfolio_with_ou_template.has_resource_properties(
            "AWS::CloudFormation::StackSet",
            {
                "PermissionModel": "SERVICE_MANAGED",
                "CallAs": "DELEGATED_ADMIN",
                "Capabilities": ["CAPABILITY_NAMED_IAM"],
            },
        )

    def test_stackset_targets_correct_ou(self, portfolio_with_ou_template):
        portfolio_with_ou_template.has_resource_properties(
            "AWS::CloudFormation::StackSet",
            {
                "StackInstancesGroup": Match.array_with([
                    Match.object_like({
                        "DeploymentTargets": {
                            "OrganizationalUnitIds": ["ou-abcd-12345678"],
                        },
                    }),
                ]),
            },
        )

    def test_stackset_auto_deployment_enabled(self, portfolio_with_ou_template):
        portfolio_with_ou_template.has_resource_properties(
            "AWS::CloudFormation::StackSet",
            {
                "AutoDeployment": {
                    "Enabled": True,
                    "RetainStacksOnAccountRemoval": False,
                },
            },
        )

    def test_no_stackset_without_ous(self, portfolio_template):
        portfolio_template.resource_count_is("AWS::CloudFormation::StackSet", 0)


class TestMultipleProducts:

    def test_two_products_create_two_roles(self):
        app = App()
        env = Environment(account="123456789012", region="us-east-1")

        assets_stack = AssetsStack(
            app, "Assets",
            organization_id="o-abc123def456",
            env=env,
        )

        config = _make_portfolio_config(products=[
            ProductConfig(
                name="s3-bucket",
                template="../templates/storage/s3-research-bucket.yaml",
                display_name="S3 Bucket",
                launch_role_policies=["AmazonS3FullAccess"],
            ),
            ProductConfig(
                name="efs-storage",
                template="../templates/storage/efs-shared-storage.yaml",
                display_name="EFS Storage",
                launch_role_policies=["AmazonElasticFileSystemFullAccess", "AmazonEC2FullAccess"],
            ),
        ])

        stack = PortfolioStack(
            app, "MultiProduct",
            portfolio_config=config,
            asset_bucket=assets_stack.assets_bucket,
            env=env,
        )
        template = Template.from_stack(stack)

        # Two products
        template.resource_count_is("AWS::ServiceCatalog::CloudFormationProduct", 2)
        # Two launch roles (one per product)
        # Count IAM roles — there will be 2 launch roles + potentially custom resource roles
        roles = template.find_resources("AWS::IAM::Role")
        launch_roles = [
            r for r in roles.values()
            if "servicecatalog.amazonaws.com" in str(r)
        ]
        assert len(launch_roles) == 2


class TestErrorHandling:

    def test_missing_template_raises(self):
        app = App()
        env = Environment(account="123456789012", region="us-east-1")

        assets_stack = AssetsStack(
            app, "Assets",
            organization_id="o-abc123def456",
            env=env,
        )

        config = _make_portfolio_config(products=[
            ProductConfig(
                name="bad-product",
                template="../templates/nonexistent.yaml",
                display_name="Bad Product",
                launch_role_policies=[],
            ),
        ])

        with pytest.raises(FileNotFoundError, match="nonexistent"):
            PortfolioStack(
                app, "BadPortfolio",
                portfolio_config=config,
                asset_bucket=assets_stack.assets_bucket,
                env=env,
            )


class TestTagging:

    def test_standard_tags_applied(self):
        from utils.tagging import apply_standard_tags

        app = App()
        env = Environment(account="123456789012", region="us-east-1")

        assets_stack = AssetsStack(
            app, "Assets",
            organization_id="o-abc123def456",
            env=env,
        )

        apply_standard_tags(app, "test")
        template = Template.from_stack(assets_stack)

        # CDK tags are applied at the stack level — they appear in the template
        # as Tags on resources. Check that at least the bucket has the tags.
        assets_template_json = template.to_json()
        template_str = str(assets_template_json)
        assert "ResearchStack" in template_str
        assert "DeployedBy" in template_str or "CDK" in template_str


class TestLaunchRoleDetails:

    def test_cloudformation_full_access_always_included(self):
        """Launch role should always have AWSCloudFormationFullAccess even if not declared."""
        app = App()
        env = Environment(account="123456789012", region="us-east-1")

        assets_stack = AssetsStack(
            app, "Assets",
            organization_id="o-abc123def456",
            env=env,
        )

        # Product only declares S3 access, not CloudFormation
        config = _make_portfolio_config(products=[
            ProductConfig(
                name="s3-only",
                template="../templates/storage/s3-research-bucket.yaml",
                display_name="S3 Only",
                launch_role_policies=["AmazonS3FullAccess"],
            ),
        ])

        stack = PortfolioStack(
            app, "CFNAccessTest",
            portfolio_config=config,
            asset_bucket=assets_stack.assets_bucket,
            env=env,
        )
        template = Template.from_stack(stack)

        # Find the launch role and check it has CloudFormation policy
        roles = template.find_resources("AWS::IAM::Role")
        launch_role = [
            r for r in roles.values()
            if "servicecatalog.amazonaws.com" in str(r)
        ]
        assert len(launch_role) == 1
        role_str = str(launch_role[0])
        assert "AWSCloudFormationFullAccess" in role_str

    def test_launch_role_has_s3_inline_policy(self):
        """Launch role should have inline S3 policy for reading SC template artifacts."""
        app = App()
        env = Environment(account="123456789012", region="us-east-1")

        assets_stack = AssetsStack(
            app, "Assets",
            organization_id="o-abc123def456",
            env=env,
        )

        config = _make_portfolio_config()
        stack = PortfolioStack(
            app, "InlinePolicyTest",
            portfolio_config=config,
            asset_bucket=assets_stack.assets_bucket,
            env=env,
        )
        template = Template.from_stack(stack)

        # The launch role should have an inline policy for S3 GetObject
        roles = template.find_resources("AWS::IAM::Role")
        launch_role = [
            r for r in roles.values()
            if "servicecatalog.amazonaws.com" in str(r)
        ]
        role_str = str(launch_role[0])
        assert "s3:GetObject" in role_str
        assert "servicecatalog:provisioning" in role_str


class TestStackSetFactory:

    def test_no_targets_raises_value_error(self):
        """StacksetFactory should raise if neither OUs nor accounts provided."""
        from sc_constructs.stackset_factory import StacksetFactory
        from sc_constructs.launch_role_stackset_template import LaunchRoleStacksetProps

        app = App()
        env = Environment(account="123456789012", region="us-east-1")
        assets_stack = AssetsStack(
            app, "Assets",
            organization_id="o-abc123def456",
            env=env,
        )

        config = _make_portfolio_config()
        stack = PortfolioStack(
            app, "FactoryTest",
            portfolio_config=config,
            asset_bucket=assets_stack.assets_bucket,
            env=env,
        )

        props = LaunchRoleStacksetProps(
            product_name="test-product",
            portfolio_name="test-portfolio",
            managed_policy_names=["AmazonS3FullAccess"],
        )

        with pytest.raises(ValueError, match="Either target_accounts or target_ou_ids"):
            stack.stackset_factory.create_launch_role_stackset(
                stack_name="test-stackset",
                props=props,
                target_regions=["us-east-1"],
                # Neither target_ou_ids nor target_accounts provided
            )
