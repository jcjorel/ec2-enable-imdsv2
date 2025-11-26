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
    errors: int,
    account_defaults_stats: dict = None
) -> tuple:
    """
    Print scan summary and ask for confirmation
    
    Args:
        regions_count: Number of regions scanned
        total_instances: Total number of instances found
        needs_update: Number of instances needing IMDSv2 enforcement
        already_compliant: Number of instances already compliant
        errors: Number of errors encountered
        account_defaults_stats: Optional dict with account defaults statistics
        
    Returns:
        Tuple of (proceed_with_instances, proceed_with_account_defaults)
    """
    print(SEPARATOR)
    print("Scan Summary:")
    print(f"  Total regions scanned: {regions_count}")
    print(f"  Total instances found: {total_instances}")
    print(f"  Instances requiring IMDSv2 enforcement: {needs_update}")
    print(f"  Instances already compliant: {already_compliant}")
    
    # Display account defaults status if provided
    if account_defaults_stats:
        print()
        print("Account-Level Defaults (for new instances):")
        print(f"  Regions with 'required': {account_defaults_stats['required']}")
        print(f"  Regions with 'optional': {account_defaults_stats['optional']}")
        print(f"  Regions not set: {account_defaults_stats['not_set']}")
        print(f"  Regions needing update: {account_defaults_stats['needs_update']}")
    
    print(f"  Errors encountered: {errors}")
    print()
    
    proceed_instances = False
    proceed_account = False
    
    # Ask about instances
    if needs_update > 0:
        while True:
            response = input(f"Enable IMDSv2 enforcement on {needs_update} existing instance(s)? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                proceed_instances = True
                break
            elif response in ['no', 'n']:
                break
            else:
                print("Please answer 'yes' or 'no'")
    else:
        print("✓ All instances already have IMDSv2 enforcement enabled!")
    
    # Ask about account defaults
    if account_defaults_stats and account_defaults_stats['needs_update'] > 0:
        print()
        while True:
            response = input(f"Set account-level defaults to 'required' in {account_defaults_stats['needs_update']} region(s)? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                proceed_account = True
                break
            elif response in ['no', 'n']:
                break
            else:
                print("Please answer 'yes' or 'no'")
    elif account_defaults_stats:
        print()
        print("✓ All regions already have account-level defaults set to 'required'!")
    
    if not proceed_instances and not proceed_account:
        print("\nNo changes to apply.")
    
    return proceed_instances, proceed_account


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