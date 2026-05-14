# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""S3 bucket for Service Catalog template artifacts.

Member accounts in the org get read access so SC can launch products
from templates stored here. One bucket shared across all portfolios.
"""

import logging

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

from utils.config import GlobalConfig
from utils.resource_naming import ResourceNaming

logger = logging.getLogger(__name__)


class AssetsStack(Stack):
    """Creates the SC assets S3 bucket with org-wide read access."""

    def __init__(self, scope: Construct, construct_id: str, *, organization_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        slug = GlobalConfig.get_project_slug().lower().replace("_", "-")
        env_name = GlobalConfig.get_env_name()
        account_id = Stack.of(self).account
        region = Stack.of(self).region
        bucket_name = ResourceNaming.sanitize_name(
            f"{slug}-assets-{env_name}-{account_id}-{region}"
        )

        self.assets_bucket = s3.Bucket(
            self,
            "SCAssetsBucket",
            bucket_name=bucket_name,
            versioned=True,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(0),
                        )
                    ]
                )
            ],
        )

        # Allow member accounts in the org to read template artifacts
        self.assets_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.OrganizationPrincipal(organization_id)],
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    f"{self.assets_bucket.bucket_arn}/*",
                    self.assets_bucket.bucket_arn,
                ],
            )
        )

        CfnOutput(self, "AssetsBucketName", value=self.assets_bucket.bucket_name)
        CfnOutput(self, "AssetsBucketArn", value=self.assets_bucket.bucket_arn)
