# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for Service Catalog tests."""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    """Path to test fixture files."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def valid_framework_config(fixtures_dir):
    """Path to a valid framework_config.yaml fixture."""
    return fixtures_dir / "valid_framework_config.yaml"


@pytest.fixture
def valid_portfolio_dir(fixtures_dir):
    """Path to a directory with valid portfolio TOML fixtures."""
    return fixtures_dir / "portfolios"
