"""EC2 IMDSv2 Enforcement Tool

This package provides a CLI tool to enable IMDSv2 enforcement on EC2 instances
across all AWS regions in an account.
"""

__version__ = "1.0.0"
__author__ = "EC2 IMDSv2 Tool"

from . import (
    error_handler,
    aws_session,
    region_scanner,
    instance_scanner,
    instance_modifier,
    account_defaults,
    reporter,
    cli
)

__all__ = [
    'error_handler',
    'aws_session',
    'region_scanner',
    'instance_scanner',
    'instance_modifier',
    'account_defaults',
    'reporter',
    'cli',
]