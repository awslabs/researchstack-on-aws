"""cdk-nag compliance tests for Service Catalog stacks.

Validates that synthesized stacks follow AWS Solutions best practices.
Findings are either clean or explicitly suppressed with justification.
"""

import pytest
from aws_cdk import App, Aspects, Environment
from aws_cdk.assertions import Annotations, Match
from cdk_nag import AwsSolutionsChecks, NagSuppressions

from core.portfolio_config import PortfolioConfig, ProductConfig
from stacks.assets_stack import AssetsStack
from stacks.portfolio_stack import PortfolioStack
from utils.config import GlobalConfig


@pytest.fixture(autouse=True)
def reset_globals():
    GlobalConfig.env_name = "test"
    GlobalConfig.project_slug = "rs"


def _synth_assets_stack():
    """Synth the assets stack with cdk-nag and justified suppressions."""
    app = App()
    env = Environment(account="123456789012", region="us-east-1")
    stack = AssetsStack(app, "Assets", organization_id="o-abc123def456", env=env)

    NagSuppressions.add_resource_suppressions(
        stack.assets_bucket,
        [
            {
                "id": "AwsSolutions-S1",
                "reason": "Assets bucket stores SC templates only — no user data, "
                "no access surface beyond org-scoped GetObject. "
                "Access logging would require a second bucket for zero value.",
            },
        ],
    )

    Aspects.of(stack).add(AwsSolutionsChecks())
    app.synth()
    return stack


def _synth_portfolio_stack(target_ous=None):
    """Synth the portfolio stack with cdk-nag and justified suppressions."""
    app = App()
    env = Environment(account="123456789012", region="us-east-1")

    assets = AssetsStack(app, "Assets", organization_id="o-abc123def456", env=env)

    config = PortfolioConfig(
        name="test-portfolio",
        display_name="Test Portfolio",
        description="Test",
        provider_name="Test Provider",
        products=[
            ProductConfig(
                name="s3-research-bucket",
                template="../templates/storage/s3-research-bucket.yaml",
                display_name="Storage Bucket",
                launch_role_policies=["AmazonS3FullAccess"],
            ),
        ],
        target_ous=target_ous or ["ou-abcd-12345678"],
        access_principals=[],
        share_tag_options=True,
        share_principals=True,
    )

    stack = PortfolioStack(
        app, "Portfolio",
        portfolio_config=config,
        asset_bucket=assets.assets_bucket,
        env=env,
    )

    # --- Suppressions with justification ---

    # CDK's AwsCustomResource for portfolio sharing uses a Lambda with a
    # managed execution role and SDK calls requiring broad permissions.
    # These are CDK-internal constructs, not user-authored.
    NagSuppressions.add_stack_suppressions(
        stack,
        [
            {
                "id": "AwsSolutions-L1",
                "reason": "Lambda runtime is managed by CDK AwsCustomResource construct — "
                "not user-controlled. Updates come via CDK version bumps.",
            },
        ],
    )

    NagSuppressions.add_stack_suppressions(
        stack,
        [
            {
                "id": "AwsSolutions-IAM4",
                "applies_to": [
                    "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                ],
                "reason": "AWSLambdaBasicExecutionRole is the standard minimal policy for "
                "Lambda logging. Required by CDK AwsCustomResource.",
            },
            {
                "id": "AwsSolutions-IAM4",
                "applies_to": [
                    "Policy::arn:<AWS::Partition>:iam::aws:policy/AmazonS3FullAccess",
                    "Policy::arn:<AWS::Partition>:iam::aws:policy/AWSCloudFormationFullAccess",
                ],
                "reason": "SC launch roles use AWS managed policies declared in portfolio TOML. "
                "These are required for SC to provision CloudFormation stacks on behalf "
                "of researchers. Scoped per-product — each product gets only the policies it needs.",
            },
        ],
    )

    NagSuppressions.add_stack_suppressions(
        stack,
        [
            {
                "id": "AwsSolutions-IAM5",
                "applies_to": ["Resource::*"],
                "reason": "Wildcard resources on launch roles: (1) S3 inline policy uses "
                "servicecatalog:provisioning condition key to scope access to SC-managed "
                "objects only. (2) Portfolio share custom resource needs servicecatalog:* "
                "on the portfolio — CDK generates the policy, not user code.",
            },
        ],
    )

    Aspects.of(stack).add(AwsSolutionsChecks())
    app.synth()
    return stack


class TestAssetsStackNag:

    def test_no_unsuppressed_errors(self):
        stack = _synth_assets_stack()
        annotations = Annotations.from_stack(stack)
        annotations.has_no_error("*", Match.string_like_regexp("AwsSolutions-.*"))

    def test_no_warnings(self):
        stack = _synth_assets_stack()
        annotations = Annotations.from_stack(stack)
        annotations.has_no_warning("*", Match.string_like_regexp("AwsSolutions-.*"))


class TestPortfolioStackNag:

    def test_no_unsuppressed_errors(self):
        stack = _synth_portfolio_stack()
        annotations = Annotations.from_stack(stack)
        annotations.has_no_error("*", Match.string_like_regexp("AwsSolutions-.*"))

    def test_no_unsuppressed_warnings(self):
        stack = _synth_portfolio_stack()
        annotations = Annotations.from_stack(stack)
        annotations.has_no_warning("*", Match.string_like_regexp("AwsSolutions-.*"))
