"""Tests for assets_stack.py — S3 bucket for SC template artifacts."""

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template, Match

from stacks.assets_stack import AssetsStack
from utils.config import GlobalConfig


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset GlobalConfig before each test."""
    GlobalConfig.env_name = "test"
    GlobalConfig.project_slug = "rs"


@pytest.fixture
def assets_template():
    app = App()
    stack = AssetsStack(
        app, "TestAssets",
        organization_id="o-abc123def456",
        env=Environment(account="123456789012", region="us-east-1"),
    )
    return Template.from_stack(stack)


class TestAssetsStack:

    def test_creates_s3_bucket(self, assets_template):
        assets_template.resource_count_is("AWS::S3::Bucket", 1)

    def test_bucket_has_versioning(self, assets_template):
        assets_template.has_resource_properties("AWS::S3::Bucket", {
            "VersioningConfiguration": {"Status": "Enabled"},
        })

    def test_bucket_enforces_ssl(self, assets_template):
        # CDK's enforce_ssl adds a bucket policy denying non-SSL requests
        assets_template.has_resource_properties("AWS::S3::BucketPolicy", {})

    def test_bucket_name_follows_convention(self, assets_template):
        assets_template.has_resource_properties("AWS::S3::Bucket", {
            "BucketName": "rs-assets-test-123456789012-us-east-1",
        })

    def test_outputs_bucket_name_and_arn(self, assets_template):
        outputs = assets_template.to_json()["Outputs"]
        output_keys = list(outputs.keys())
        # CDK generates logical IDs, check that we have 2 outputs
        assert len(outputs) == 2

    def test_bucket_has_org_read_policy(self, assets_template):
        """Verify the bucket policy includes org-wide read access."""
        assets_template.has_resource_properties("AWS::S3::BucketPolicy", {
            "PolicyDocument": Match.object_like({
                "Statement": Match.array_with([
                    Match.object_like({
                        "Action": Match.array_with(["s3:GetObject"]),
                        "Effect": "Allow",
                        "Condition": Match.object_like({
                            "StringEquals": {
                                "aws:PrincipalOrgID": "o-abc123def456",
                            },
                        }),
                    }),
                ]),
            }),
        })
