# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Apply standard tags to all CDK stacks."""

from aws_cdk import Stack, Tags
from constructs import Construct


def apply_standard_tags(scope: Construct, env_name: str):
    """Apply Project, Environment, DeployedBy tags to all stacks in scope."""
    _apply_tags(scope, env_name)


def _apply_tags(construct: Construct, env_name: str):
    if isinstance(construct, Stack):
        Tags.of(construct).add("Project", "ResearchStack")
        Tags.of(construct).add("Environment", env_name)
        Tags.of(construct).add("DeployedBy", "CDK")
    for child in construct.node.children:
        if isinstance(child, Construct):
            _apply_tags(child, env_name)
