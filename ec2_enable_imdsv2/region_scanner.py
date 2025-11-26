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
        # Get region from session or use default us-east-1
        region = session.region_name if session.region_name else 'us-east-1'
        ec2 = session.client('ec2', region_name=region)
        
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