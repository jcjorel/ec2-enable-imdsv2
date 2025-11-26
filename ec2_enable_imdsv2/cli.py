"""Main CLI entry point for EC2 IMDSv2 enforcement tool"""

import argparse
import sys
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import (
    aws_session,
    region_scanner,
    instance_scanner,
    instance_modifier,
    account_defaults,
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


def scan_region_wrapper(session, region: str) -> tuple:
    """
    Wrapper function to scan a single region
    
    Args:
        session: boto3 Session object
        region: Region name to scan
        
    Returns:
        Tuple of (region, instances_list)
    """
    instances = instance_scanner.scan_region(session, region)
    return region, instances


def scan_phase(session, regions: List[str]) -> tuple:
    """
    Phase 1: Scan all regions and instances in parallel, and check account defaults
    
    Args:
        session: boto3 Session object
        regions: List of region names to scan
    
    Returns:
        Tuple of (all_instances, instances_needing_update, account_defaults_dict)
    """
    print(f"Scanning {len(regions)} regions in parallel...")
    print("  - Checking instances")
    print("  - Checking account-level defaults")
    print()
    
    all_instances = []
    region_results = {}
    
    # Scan all regions in parallel using ThreadPoolExecutor
    max_workers = min(len(regions), 15)  # Limit to 15 concurrent threads
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all region scan tasks
        future_to_region = {
            executor.submit(scan_region_wrapper, session, region): region
            for region in regions
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_region):
            region = future_to_region[future]
            try:
                region_name, instances = future.result()
                region_results[region_name] = instances
                all_instances.extend(instances)
                # Print progress indicator
                print(f"  ✓ Scanned {region_name}: {len(instances)} instance(s) found")
            except Exception as e:
                error_handler.error_tracker.log_error('scan_phase', e, region=region)
                region_results[region] = []
    
    # Check account defaults in parallel
    print()
    print("Checking account-level defaults...")
    account_defaults_dict = account_defaults.check_account_defaults_parallel(session, regions)
    print("  ✓ Account defaults checked")
    
    print()
    print("Scan Results:")
    print("=" * 80)
    print()
    
    # Print results in order of regions
    for region in sorted(region_results.keys()):
        instances = region_results[region]
        reporter.print_region_header(region)
        reporter.print_region_scan_results(region, instances)
    
    instances_needing_update = instance_scanner.get_instances_needing_update(all_instances)
    
    return all_instances, instances_needing_update, account_defaults_dict


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


def apply_account_defaults_phase(session, account_defaults_dict: dict) -> List:
    """
    Phase 3: Apply account-level IMDS defaults
    
    Args:
        session: boto3 Session object
        account_defaults_dict: Dictionary mapping region to current HttpTokens value
        
    Returns:
        List of AccountDefaultResult objects
    """
    print()
    print("Setting Account-Level Defaults...")
    print("=" * 80)
    print()
    print("ℹ This sets defaults for NEW instances only. Existing instances are not affected.")
    print()
    
    # Filter regions that need updating
    regions_to_update = [
        region for region, tokens in account_defaults_dict.items()
        if tokens != 'required'
    ]
    
    # Modify account defaults in parallel
    results = account_defaults.modify_account_defaults_parallel(session, regions_to_update)
    
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
        
        # Phase 1: Scan (instances and account defaults)
        reporter.print_scan_header(args.profile, account_id)
        
        start_time = time.time()
        all_instances, instances_needing_update, account_defaults_dict = scan_phase(session, regions)
        
        # Get statistics
        stats = instance_scanner.get_summary_stats(all_instances)
        account_stats = account_defaults.get_account_defaults_stats(account_defaults_dict)
        
        # Print summary and get confirmation
        proceed_instances, proceed_account = reporter.print_scan_summary(
            regions_count=len(regions),
            total_instances=stats['total'],
            needs_update=stats['needs_update'],
            already_compliant=stats['already_compliant'],
            errors=error_handler.error_tracker.get_error_count(),
            account_defaults_stats=account_stats
        )
        
        if not proceed_instances and not proceed_account:
            sys.exit(0)
        
        instance_results = []
        account_results = []
        
        # Phase 2: Modify instances if requested
        if proceed_instances:
            instance_results = modification_phase(session, instances_needing_update)
        
        # Phase 3: Apply account defaults if requested
        if proceed_account:
            account_results = apply_account_defaults_phase(session, account_defaults_dict)
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # Print final summary for instances
        if proceed_instances:
            mod_summary = instance_modifier.get_modification_summary(instance_results)
            reporter.print_final_summary(
                successful=mod_summary['successful'],
                failed=mod_summary['failed'],
                elapsed_time=elapsed_time,
                error_details=mod_summary['error_details']
            )
        
        # Print final summary for account defaults
        if proceed_account:
            account_summary = account_defaults.get_account_defaults_summary(account_results)
            print()
            print("=" * 80)
            print("Account Defaults Summary:")
            print(f"  Regions successfully updated: {account_summary['successful']}")
            print(f"  Regions failed to update: {account_summary['failed']}")
            
            if account_summary['error_details']:
                print()
                print("Detailed error log:")
                for error in account_summary['error_details']:
                    print(f"  - {error}")
            
            print()
            
            if account_summary['failed'] == 0:
                print("✓ All regions successfully configured with IMDSv2 account defaults!")
                print("ℹ New instances will now require IMDSv2 by default.")
            else:
                print(f"⚠ Completed with {account_summary['failed']} error(s).")
        
        # Exit with appropriate code
        any_failures = (
            (proceed_instances and instance_modifier.get_modification_summary(instance_results)['failed'] > 0) or
            (proceed_account and account_defaults.get_account_defaults_summary(account_results)['failed'] > 0)
        )
        sys.exit(0 if not any_failures else 1)
        
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