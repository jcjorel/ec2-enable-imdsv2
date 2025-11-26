# EC2 IMDSv2 Enforcement Tool - Implementation Guide

This document provides detailed implementation specifications and code templates for each module of the EC2 IMDSv2 enforcement tool.

## Module Implementation Order

Implement modules in this order to maintain dependency flow:

1. `error_handler.py` - No dependencies
2. `aws_session.py` - Depends on error_handler
3. `region_scanner.py` - Depends on aws_session, error_handler
4. `instance_scanner.py` - Depends on aws_session, error_handler
5. `instance_modifier.py` - Depends on aws_session, error_handler
6. `reporter.py` - Depends on instance_scanner, instance_modifier
7. `cli.py` - Depends on all above modules

## Module 1: error_handler.py

### Purpose
Centralized error tracking and logging system for the application.

### Code Template

```python
"""Error handling and tracking for EC2 IMDSv2 enforcement tool"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import sys


@dataclass
class ErrorRecord:
    """Record of an error that occurred during execution"""
    timestamp: datetime
    component: str
    region: Optional[str]
    instance_id: Optional[str]
    error_type: str
    error_message: str
    
    def __str__(self) -> str:
        """Format error for display"""
        parts = [f"[{self.component}]"]
        if self.region:
            parts.append(f"Region: {self.region}")
        if self.instance_id:
            parts.append(f"Instance: {self.instance_id}")
        parts.append(f"{self.error_type}: {self.error_message}")
        return " - ".join(parts)


class ErrorTracker:
    """Singleton class to track errors across the application"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.errors: List[ErrorRecord] = []
        return cls._instance
    
    def log_error(
        self,
        component: str,
        error: Exception,
        region: Optional[str] = None,
        instance_id: Optional[str] = None
    ) -> None:
        """
        Log an error for later reporting
        
        Args:
            component: Name of the component where error occurred
            error: The exception that was raised
            region: AWS region where error occurred (if applicable)
            instance_id: EC2 instance ID where error occurred (if applicable)
        """
        record = ErrorRecord(
            timestamp=datetime.now(),
            component=component,
            region=region,
            instance_id=instance_id,
            error_type=type(error).__name__,
            error_message=str(error)
        )
        self.errors.append(record)
        
        # Print error immediately for visibility
        print(f"  ✗ Error: {record}", file=sys.stderr)
    
    def get_error_summary(self) -> List[str]:
        """
        Get formatted list of error messages
        
        Returns:
            List of formatted error strings
        """
        return [str(error) for error in self.errors]
    
    def has_errors(self) -> bool:
        """
        Check if any errors were logged
        
        Returns:
            True if errors exist, False otherwise
        """
        return len(self.errors) > 0
    
    def get_error_count(self) -> int:
        """
        Get total count of errors
        
        Returns:
            Number of errors logged
        """
        return len(self.errors)
    
    def reset(self) -> None:
        """Clear all logged errors"""
        self.errors.clear()


# Global error tracker instance
error_tracker = ErrorTracker()
```

### Key Implementation Notes
- Uses singleton pattern for global access
- Immediately prints errors to stderr for visibility
- Stores full error context for later reporting
- Thread-safe for potential future parallelization

---

## Module 2: aws_session.py

### Purpose
Manage AWS session initialization and credential validation.

### Code Template

```python
"""AWS session management for EC2 IMDSv2 enforcement tool"""

import boto3
from botocore.exceptions import (
    ProfileNotFound,
    NoCredentialsError,
    ClientError
)
from typing import Optional

from .error_handler import error_tracker


def create_session(profile_name: str) -> boto3.Session:
    """
    Create boto3 session with specified profile
    
    Args:
        profile_name: AWS profile name from ~/.aws/credentials or ~/.aws/config
        
    Returns:
        boto3.Session object configured with the profile
        
    Raises:
        ProfileNotFound: If the specified profile doesn't exist
        NoCredentialsError: If credentials are not properly configured
        SystemExit: If credentials cannot be validated
    """
    try:
        session = boto3.Session(profile_name=profile_name)
        
        # Validate credentials by calling STS
        validate_credentials(session)
        
        return session
        
    except ProfileNotFound:
        print(f"\n✗ Error: AWS profile '{profile_name}' not found")
        print(f"  Available profiles can be listed with: aws configure list-profiles")
        print(f"  Configure a new profile with: aws configure --profile {profile_name}")
        raise SystemExit(1)
        
    except NoCredentialsError:
        print(f"\n✗ Error: No credentials configured for profile '{profile_name}'")
        print(f"  Configure credentials with: aws configure --profile {profile_name}")
        raise SystemExit(1)


def validate_credentials(session: boto3.Session) -> dict:
    """
    Validate AWS credentials and get caller identity
    
    Args:
        session: boto3 Session object
        
    Returns:
        Dictionary with account_id, user_id, and arn
        
    Raises:
        SystemExit: If credentials are invalid or lack permissions
    """
    try:
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        
        return {
            'account_id': identity['Account'],
            'user_id': identity['UserId'],
            'arn': identity['Arn']
        }
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        
        print(f"\n✗ Error: Failed to validate AWS credentials")
        print(f"  Error Code: {error_code}")
        print(f"  Message: {error_msg}")
        
        if error_code == 'InvalidClientTokenId':
            print(f"  Suggestion: Check that your access key is correct")
        elif error_code == 'SignatureDoesNotMatch':
            print(f"  Suggestion: Check that your secret key is correct")
        
        raise SystemExit(1)


def get_account_id(session: boto3.Session) -> str:
    """
    Get AWS account ID for the session
    
    Args:
        session: boto3 Session object
        
    Returns:
        AWS account ID string
    """
    identity = validate_credentials(session)
    return identity['account_id']


def check_required_permissions(session: boto3.Session) -> bool:
    """
    Check if the session has required EC2 permissions
    
    Args:
        session: boto3 Session object
        
    Returns:
        True if all required permissions are available
        
    Note:
        This performs a dry-run check, not exhaustive permission validation
    """
    try:
        ec2 = session.client('ec2')
        
        # Test describe_regions permission
        ec2.describe_regions(DryRun=True)
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        
        # DryRunOperation means we have the permission
        if error_code == 'DryRunOperation':
            return True
        
        # UnauthorizedOperation means we lack permission
        if error_code == 'UnauthorizedOperation':
            print(f"\n⚠ Warning: Missing ec2:DescribeRegions permission")
            print(f"  This tool requires the following IAM permissions:")
            print(f"    - ec2:DescribeRegions")
            print(f"    - ec2:DescribeInstances")
            print(f"    - ec2:ModifyInstanceMetadataOptions")
            return False
        
        # Other errors
        error_tracker.log_error('permission_check', e)
        return False
    
    return True
```

### Key Implementation Notes
- Validates credentials immediately on session creation
- Provides helpful error messages with remediation steps
- Performs permission checks with dry-run mode
- Gracefully handles common authentication errors

---

## Module 3: region_scanner.py

### Purpose
Discover and enumerate enabled AWS regions for the account.

### Code Template

```python
"""Region discovery and enumeration for EC2 IMDSv2 enforcement tool"""

import boto3
from botocore.exceptions import ClientError
from typing import List

from .error_handler import error_tracker


def get_enabled_regions(session: boto3.Session) -> List[str]:
    """
    Get list of all enabled regions for the account
    
    Args:
        session: boto3 Session object
        
    Returns:
        Sorted list of region names (e.g., ['us-east-1', 'eu-west-1'])
        Returns empty list if unable to retrieve regions
    """
    try:
        ec2 = session.client('ec2')
        
        response = ec2.describe_regions(
            AllRegions=False,
            Filters=[
                {
                    'Name': 'opt-in-status',
                    'Values': ['opt-in-not-required', 'opted-in']
                }
            ]
        )
        
        regions = [r['RegionName'] for r in response['Regions']]
        return sorted(regions)
        
    except ClientError as e:
        error_tracker.log_error('region_scanner', e)
        print(f"\n✗ Fatal Error: Unable to retrieve AWS regions")
        print(f"  This is required to proceed. Please check your permissions.")
        return []


def is_region_accessible(session: boto3.Session, region: str) -> bool:
    """
    Check if a region is accessible with current credentials
    
    Args:
        session: boto3 Session object
        region: Region name to check
        
    Returns:
        True if region is accessible, False otherwise
    """
    try:
        ec2 = session.client('ec2', region_name=region)
        # Simple API call to test accessibility
        ec2.describe_instances(MaxResults=5)
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        
        # These are expected errors for inaccessible regions
        if error_code in ['UnauthorizedOperation', 'OptInRequired']:
            return False
        
        # Log other unexpected errors
        error_tracker.log_error('region_scanner', e, region=region)
        return False


def validate_region_access(session: boto3.Session, regions: List[str]) -> List[str]:
    """
    Validate access to regions and filter out inaccessible ones
    
    Args:
        session: boto3 Session object
        regions: List of region names to validate
        
    Returns:
        List of accessible region names
    """
    accessible = []
    
    for region in regions:
        if is_region_accessible(session, region):
            accessible.append(region)
        else:
            print(f"  ⚠ Skipping region {region}: Not accessible")
    
    return accessible
```

### Key Implementation Notes
- Filters for only opted-in regions
- Returns sorted list for consistent output
- Validates region accessibility before processing
- Handles region-specific permission errors gracefully

---

## Module 4: instance_scanner.py

### Purpose
Discover EC2 instances and assess their IMDSv2 enforcement status.

### Code Template

```python
"""EC2 instance scanning for IMDSv2 status"""

import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .error_handler import error_tracker


@dataclass
class InstanceInfo:
    """Information about an EC2 instance and its IMDSv2 status"""
    instance_id: str
    region: str
    state: str
    http_tokens: Optional[str]
    http_endpoint: Optional[str]
    needs_update: bool
    instance_name: Optional[str] = None
    
    def __str__(self) -> str:
        """Format instance info for display"""
        name_part = f" ({self.instance_name})" if self.instance_name else ""
        status = "NOT enforced" if self.needs_update else "already enforced ✓"
        token_value = self.http_tokens if self.http_tokens else "not set"
        return (f"Instance {self.instance_id}{name_part} [{self.state}]: "
                f"IMDSv2 {status} (HttpTokens: {token_value})")


def scan_region(session: boto3.Session, region: str) -> List[InstanceInfo]:
    """
    Scan a region for EC2 instances and their IMDSv2 status
    
    Args:
        session: boto3 Session object
        region: Region name to scan
        
    Returns:
        List of InstanceInfo objects for instances in the region
    """
    instances = []
    
    try:
        ec2 = session.client('ec2', region_name=region)
        
        # Use paginator to handle large numbers of instances
        paginator = ec2.get_paginator('describe_instances')
        page_iterator = paginator.paginate()
        
        for page in page_iterator:
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    instance_info = parse_instance(instance, region)
                    instances.append(instance_info)
        
    except ClientError as e:
        error_tracker.log_error('instance_scanner', e, region=region)
    
    return instances


def parse_instance(instance: dict, region: str) -> InstanceInfo:
    """
    Parse instance data from describe_instances response
    
    Args:
        instance: Instance dictionary from describe_instances
        region: Region name
        
    Returns:
        InstanceInfo object
    """
    instance_id = instance['InstanceId']
    state = instance['State']['Name']
    
    # Get instance name from tags
    instance_name = None
    for tag in instance.get('Tags', []):
        if tag['Key'] == 'Name':
            instance_name = tag['Value']
            break
    
    # Check metadata options
    metadata_opts = instance.get('MetadataOptions', {})
    http_tokens = metadata_opts.get('HttpTokens')
    http_endpoint = metadata_opts.get('HttpEndpoint', 'enabled')
    
    # Determine if update is needed
    needs_update = check_needs_update(http_tokens)
    
    return InstanceInfo(
        instance_id=instance_id,
        region=region,
        state=state,
        http_tokens=http_tokens,
        http_endpoint=http_endpoint,
        needs_update=needs_update,
        instance_name=instance_name
    )


def check_needs_update(http_tokens: Optional[str]) -> bool:
    """
    Check if instance requires IMDSv2 enforcement
    
    Args:
        http_tokens: Current HttpTokens value from instance metadata
        
    Returns:
        True if instance needs IMDSv2 enforcement, False otherwise
    """
    # Instance needs update if HttpTokens is not 'required'
    # This includes None (not set), 'optional', or any other value
    return http_tokens != 'required'


def get_instances_needing_update(instances: List[InstanceInfo]) -> List[InstanceInfo]:
    """
    Filter instances that need IMDSv2 enforcement
    
    Args:
        instances: List of InstanceInfo objects
        
    Returns:
        Filtered list containing only instances that need updates
    """
    return [inst for inst in instances if inst.needs_update]


def get_summary_stats(instances: List[InstanceInfo]) -> dict:
    """
    Get summary statistics for a list of instances
    
    Args:
        instances: List of InstanceInfo objects
        
    Returns:
        Dictionary with summary statistics
    """
    total = len(instances)
    needs_update = sum(1 for inst in instances if inst.needs_update)
    already_compliant = total - needs_update
    
    # Count by state
    states = {}
    for inst in instances:
        states[inst.state] = states.get(inst.state, 0) + 1
    
    return {
        'total': total,
        'needs_update': needs_update,
        'already_compliant': already_compliant,
        'by_state': states
    }
```

### Key Implementation Notes
- Uses paginator to handle accounts with many instances
- Extracts instance names from tags for better identification
- Properly handles missing or unset metadata options
- Provides summary statistics for reporting

---

## Module 5: instance_modifier.py

### Purpose
Apply IMDSv2 enforcement modifications to EC2 instances.

### Code Template

```python
"""EC2 instance metadata modification for IMDSv2 enforcement"""

import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass
from typing import Optional, List
import time

from .instance_scanner import InstanceInfo
from .error_handler import error_tracker


@dataclass
class ModificationResult:
    """Result of a metadata modification operation"""
    instance_id: str
    region: str
    success: bool
    state: Optional[str] = None  # 'applied' or 'pending'
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        """Format result for display"""
        if self.success:
            return f"✓ Instance {self.instance_id}: IMDSv2 enforcement enabled (state: {self.state})"
        else:
            return f"✗ Instance {self.instance_id}: Failed - {self.error_message}"


def enable_imdsv2(
    session: boto3.Session,
    region: str,
    instance_id: str
) -> ModificationResult:
    """
    Enable IMDSv2 enforcement for a single instance
    
    Args:
        session: boto3 Session object
        region: Region name where instance is located
        instance_id: Instance ID to modify
        
    Returns:
        ModificationResult object with operation status
    """
    try:
        ec2 = session.client('ec2', region_name=region)
        
        response = ec2.modify_instance_metadata_options(
            InstanceId=instance_id,
            HttpTokens='required'
        )
        
        # Extract state from response
        state = response['InstanceMetadataOptions']['State']
        
        return ModificationResult(
            instance_id=instance_id,
            region=region,
            success=True,
            state=state
        )
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        
        error_tracker.log_error(
            'instance_modifier',
            e,
            region=region,
            instance_id=instance_id
        )
        
        return ModificationResult(
            instance_id=instance_id,
            region=region,
            success=False,
            error_message=f"{error_code}: {error_msg}"
        )


def batch_enable_imdsv2(
    session: boto3.Session,
    instances: List[InstanceInfo]
) -> List[ModificationResult]:
    """
    Enable IMDSv2 enforcement for multiple instances
    
    Args:
        session: boto3 Session object
        instances: List of InstanceInfo objects to modify
        
    Returns:
        List of ModificationResult objects
    """
    results = []
    
    for instance in instances:
        result = enable_imdsv2(
            session,
            instance.region,
            instance.instance_id
        )
        results.append(result)
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    return results


def get_modification_summary(results: List[ModificationResult]) -> dict:
    """
    Get summary statistics for modification results
    
    Args:
        results: List of ModificationResult objects
        
    Returns:
        Dictionary with summary statistics
    """
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful
    
    # Count by state for successful modifications
    states = {}
    for result in results:
        if result.success and result.state:
            states[result.state] = states.get(result.state, 0) + 1
    
    # Collect error details
    errors = [
        f"{r.region}/{r.instance_id}: {r.error_message}"
        for r in results if not r.success
    ]
    
    return {
        'total': total,
        'successful': successful,
        'failed': failed,
        'by_state': states,
        'error_details': errors
    }
```

### Key Implementation Notes
- Only modifies HttpTokens parameter (sets to 'required')
- Handles both 'pending' and 'applied' states
- Includes small delay between modifications to avoid rate limiting
- Provides detailed error messages for failures

---

## Module 6: reporter.py

### Purpose
Format and display progress, results, and summaries.

### Code Template

```python
"""Reporting and output formatting for EC2 IMDSv2 enforcement tool"""

import sys
from typing import List
from .instance_scanner import InstanceInfo
from .instance_modifier import ModificationResult


SEPARATOR = "=" * 80


def print_scan_header(profile: str, account_id: str) -> None:
    """Print header for scan phase"""
    print(f"\nScanning AWS Account using profile: {profile}")
    print(f"Account ID: {account_id}")
    print(SEPARATOR)
    print()


def print_region_header(region: str) -> None:
    """Print header when scanning a new region"""
    print(f"Region: {region}")


def print_region_scan_results(region: str, instances: List[InstanceInfo]) -> None:
    """
    Print scan results for a region
    
    Args:
        region: Region name
        instances: List of InstanceInfo objects in the region
    """
    if not instances:
        print(f"  No instances found")
    else:
        print(f"  Found {len(instances)} EC2 instance(s)")
        for instance in instances:
            print(f"  {instance}")
    print()


def print_scan_summary(
    regions_count: int,
    total_instances: int,
    needs_update: int,
    already_compliant: int,
    errors: int
) -> bool:
    """
    Print scan summary and ask for confirmation
    
    Args:
        regions_count: Number of regions scanned
        total_instances: Total number of instances found
        needs_update: Number of instances needing IMDSv2 enforcement
        already_compliant: Number of instances already compliant
        errors: Number of errors encountered
        
    Returns:
        True if user confirms to proceed, False otherwise
    """
    print(SEPARATOR)
    print("Scan Summary:")
    print(f"  Total regions scanned: {regions_count}")
    print(f"  Total instances found: {total_instances}")
    print(f"  Instances requiring IMDSv2 enforcement: {needs_update}")
    print(f"  Instances already compliant: {already_compliant}")
    print(f"  Errors encountered: {errors}")
    print()
    
    if needs_update == 0:
        print("✓ All instances already have IMDSv2 enforcement enabled!")
        return False
    
    # Ask for confirmation
    while True:
        response = input(f"Continue with enabling IMDSv2 enforcement on {needs_update} instance(s)? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            print("Operation cancelled by user")
            return False
        else:
            print("Please answer 'yes' or 'no'")


def print_modification_header() -> None:
    """Print header for modification phase"""
    print()
    print("Enabling IMDSv2 enforcement...")
    print(SEPARATOR)
    print()


def print_modification_progress(region: str, current: int, total: int) -> None:
    """
    Print progress during modifications
    
    Args:
        region: Current region being processed
        current: Current instance number
        total: Total number of instances to process
    """
    print(f"Region: {region} [{current}/{total}]")


def print_modification_result(result: ModificationResult) -> None:
    """
    Print result of a single instance modification
    
    Args:
        result: ModificationResult object
    """
    print(f"  {result}")


def print_final_summary(
    successful: int,
    failed: int,
    elapsed_time: float,
    error_details: List[str]
) -> None:
    """
    Print final summary after all modifications
    
    Args:
        successful: Number of successful modifications
        failed: Number of failed modifications
        elapsed_time: Time taken in seconds
        error_details: List of error detail strings
    """
    print()
    print(SEPARATOR)
    print("Final Summary:")
    print(f"  Instances successfully updated: {successful}")
    print(f"  Instances failed to update: {failed}")
    print(f"  Total time: {elapsed_time:.1f} seconds")
    
    if error_details:
        print()
        print("Detailed error log:")
        for error in error_details:
            print(f"  - {error}")
    
    print()
    
    if failed == 0:
        print("✓ All instances successfully updated with IMDSv2 enforcement!")
    else:
        print(f"⚠ Completed with {failed} error(s). Review the error log above.")


def print_error(message: str) -> None:
    """Print an error message to stderr"""
    print(f"✗ Error: {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning message"""
    print(f"⚠ Warning: {message}")


def print_info(message: str) -> None:
    """Print an informational message"""
    print(f"ℹ {message}")
```

### Key Implementation Notes
- Consistent formatting with separators and indentation
- Uses Unicode symbols for visual clarity (✓, ✗, ⚠)
- Interactive confirmation with validation
- Comprehensive final summary with timing information

---

## Module 7: cli.py

### Purpose
Main entry point and workflow orchestration.

### Code Template

```python
"""Main CLI entry point for EC2 IMDSv2 enforcement tool"""

import argparse
import sys
import time
from typing import List

from . import (
    aws_session,
    region_scanner,
    instance_scanner,
    instance_modifier,
    reporter,
    error_handler
)


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command line arguments"""
    parser = argparse.ArgumentParser(
        prog='ec2-enable-imdsv2',
        description='Enable IMDSv2 enforcement on EC2 instances across all AWS regions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --profile production
  %(prog)s --profile dev-account

Required AWS Permissions:
  - ec2:DescribeRegions
  - ec2:DescribeInstances
  - ec2:ModifyInstanceMetadataOptions

For more information about IMDSv2, see:
  https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html
        '''
    )
    
    parser.add_argument(
        '--profile',
        required=True,
        metavar='PROFILE',
        help='AWS profile name from ~/.aws/credentials or ~/.aws/config'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser.parse_args()


def scan_phase(session, regions: List[str]) -> tuple:
    """
    Phase 1: Scan all regions and instances
    
    Returns:
        Tuple of (all_instances, instances_needing_update)
    """
    all_instances = []
    
    for region in regions:
        reporter.print_region_header(region)
        instances = instance_scanner.scan_region(session, region)
        reporter.print_region_scan_results(region, instances)
        all_instances.extend(instances)
    
    instances_needing_update = instance_scanner.get_instances_needing_update(all_instances)
    
    return all_instances, instances_needing_update


def modification_phase(session, instances: List) -> List:
    """
    Phase 2: Apply IMDSv2 enforcement to instances
    
    Returns:
        List of ModificationResult objects
    """
    reporter.print_modification_header()
    
    results = []
    
    # Group instances by region for better progress reporting
    by_region = {}
    for inst in instances:
        if inst.region not in by_region:
            by_region[inst.region] = []
        by_region[inst.region].append(inst)
    
    # Process each region
    for region, region_instances in by_region.items():
        print(f"Region: {region}")
        
        for instance in region_instances:
            result = instance_modifier.enable_imdsv2(
                session,
                instance.region,
                instance.instance_id
            )
            results.append(result)
            reporter.print_modification_result(result)
        
        print()
    
    return results


def main():
    """Main entry point for the CLI"""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Create AWS session
        session = aws_session.create_session(args.profile)
        
        # Get account ID
        account_id = aws_session.get_account_id(session)
        
        # Check permissions
        if not aws_session.check_required_permissions(session):
            print("\n⚠ Warning: Some required permissions may be missing")
            response = input("Do you want to continue anyway? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("Exiting...")
                sys.exit(0)
        
        # Get enabled regions
        regions = region_scanner.get_enabled_regions(session)
        if not regions:
            print("\n✗ No enabled regions found. Cannot proceed.")
            sys.exit(1)
        
        # Phase 1: Scan
        reporter.print_scan_header(args.profile, account_id)
        
        start_time = time.time()
        all_instances, instances_needing_update = scan_phase(session, regions)
        
        # Get statistics
        stats = instance_scanner.get_summary_stats(all_instances)
        
        # Print summary and get confirmation
        proceed = reporter.print_scan_summary(
            regions_count=len(regions),
            total_instances=stats['total'],
            needs_update=stats['needs_update'],
            already_compliant=stats['already_compliant'],
            errors=error_handler.error_tracker.get_error_count()
        )
        
        if not proceed:
            sys.exit(0)
        
        # Phase 2: Modify
        results = modification_phase(session, instances_needing_update)
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # Get modification summary
        mod_summary = instance_modifier.get_modification_summary(results)
        
        # Print final summary
        reporter.print_final_summary(
            successful=mod_summary['successful'],
            failed=mod_summary['failed'],
            elapsed_time=elapsed_time,
            error_details=mod_summary['error_details']
        )
        
        # Exit with appropriate code
        sys.exit(0 if mod_summary['failed'] == 0 else 1)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(130)
        
    except SystemExit:
        raise
        
    except Exception as e:
        reporter.print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
```

### Key Implementation Notes
- Clean separation between scan and modification phases
- Interactive confirmation before making changes
- Comprehensive error handling with appropriate exit codes
- Progress reporting throughout execution
- Groups instances by region for clearer output

---

## Supporting Files

### requirements.txt

```
boto3>=1.34.0
botocore>=1.34.0
```

### setup.py

```python
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ec2-enable-imdsv2",
    version="1.0.0",
    author="Your Name",
    description="Enable IMDSv2 enforcement on EC2 instances across all AWS regions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "boto3>=1.34.0",
        "botocore>=1.34.0",
    ],
    entry_points={
        "console_scripts": [
            "ec2-enable-imdsv2=ec2_enable_imdsv2.cli:main",
        ],
    },
)
```

### `__init__.py` for package

```python
"""EC2 IMDSv2 Enforcement Tool

This package provides a CLI tool to enable IMDSv2 enforcement on EC2 instances
across all AWS regions in an account.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from . import (
    aws_session,
    region_scanner,
    instance_scanner,
    instance_modifier,
    reporter,
    error_handler,
    cli
)

__all__ = [
    'aws_session',
    'region_scanner',
    'instance_scanner',
    'instance_modifier',
    'reporter',
    'error_handler',
    'cli',
]
```

## Testing Approach

### Unit Tests Structure

Each module should have corresponding tests:
- `test_error_handler.py`
- `test_aws_session.py`
- `test_region_scanner.py`
- `test_instance_scanner.py`
- `test_instance_modifier.py`
- `test_reporter.py`
- `test_cli.py`

### Testing Strategy

1. **Mock boto3 clients** using `unittest.mock` or `moto` library
2. **Test error paths** - ensure errors are logged correctly
3. **Test data parsing** - verify InstanceInfo parsing logic
4. **Test user interaction** - mock stdin for confirmation prompts
5. **Integration tests** - test full workflow with mocked AWS responses

## Deployment Instructions

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install in development mode:
   ```bash
   pip install -e .
   ```

3. Or install from source:
   ```bash
   pip install .
   ```

4. Run the tool:
   ```bash
   ec2-enable-imdsv2 --profile your-profile-name
   ```

## Next Steps for Implementation

Follow this order:
1. Create project structure and supporting files
2. Implement modules in dependency order (1-7)
3. Test each module independently
4. Perform integration testing
5. Write comprehensive README
6. Add example outputs and screenshots
7. Package for distribution