# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Base class for stackset templates synthesized by StacksetFactory."""

from typing import Any, Dict, Optional

from aws_cdk import Stack
from constructs import Construct


class BaseStacksetTemplate(Stack):
    """Base for templates that get synthesized into StackSet template bodies."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        props: Dict[str, Any],
        parameters: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        self.props = props
        self.parameters = parameters or {}

    def get_parameters(self) -> Dict[str, str]:
        return self.parameters
