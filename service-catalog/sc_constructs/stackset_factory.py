"""Factory for creating CloudFormation StackSets to deploy launch roles.

Synthesizes a launch role template into a StackSet that targets OUs or accounts.
Supports SERVICE_MANAGED (OU-based) and SELF_MANAGED (account-based) permission models.
"""

import json
import logging
from typing import Dict, List, Optional

from aws_cdk import App
from aws_cdk import aws_cloudformation as cfn
from constructs import Construct

from sc_constructs.launch_role_stackset_template import (
    LaunchRoleStacksetProps,
    LaunchRoleStacksetTemplate,
)

logger = logging.getLogger(__name__)


class StacksetFactory:
    """Creates CloudFormation StackSets for deploying launch roles."""

    def __init__(self, scope: Construct, id: str) -> None:
        self.scope = scope
        self.stacksets: Dict[str, cfn.CfnStackSet] = {}

    def create_launch_role_stackset(
        self,
        stack_name: str,
        props: LaunchRoleStacksetProps,
        target_regions: List[str],
        target_ou_ids: Optional[List[str]] = None,
        target_accounts: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
    ) -> cfn.CfnStackSet:
        if not target_accounts and not target_ou_ids:
            raise ValueError("Either target_accounts or target_ou_ids must be provided")

        # Synthesize the launch role template
        temp_app = App()
        template_stack = LaunchRoleStacksetTemplate(
            temp_app, f"{stack_name}-template-synth", props=props
        )
        template = temp_app.synth().get_stack_by_name(template_stack.stack_name).template
        template_body = json.dumps(template)

        # Configure deployment targets
        if target_ou_ids:
            logger.info("OU-based deployment for: %s", target_ou_ids)
            deployment_targets = cfn.CfnStackSet.DeploymentTargetsProperty(
                organizational_unit_ids=target_ou_ids
            )
            permission_model = "SERVICE_MANAGED"
            call_as = "DELEGATED_ADMIN"
            auto_deployment = cfn.CfnStackSet.AutoDeploymentProperty(
                enabled=True, retain_stacks_on_account_removal=False
            )
        else:
            logger.info("Account-based deployment for: %s", target_accounts)
            deployment_targets = cfn.CfnStackSet.DeploymentTargetsProperty(
                accounts=target_accounts
            )
            permission_model = "SELF_MANAGED"
            call_as = None
            auto_deployment = None

        parameters = template_stack.get_parameters()

        stackset = cfn.CfnStackSet(
            self.scope,
            f"{stack_name}-stackset",
            stack_set_name=stack_name,
            template_body=template_body,
            permission_model=permission_model,
            call_as=call_as,
            capabilities=capabilities or [],
            auto_deployment=auto_deployment,
            parameters=[
                cfn.CfnStackSet.ParameterProperty(parameter_key=k, parameter_value=v)
                for k, v in parameters.items()
            ],
            stack_instances_group=[
                cfn.CfnStackSet.StackInstancesProperty(
                    regions=target_regions,
                    deployment_targets=deployment_targets,
                )
            ],
        )

        self.stacksets[stack_name] = stackset
        return stackset
