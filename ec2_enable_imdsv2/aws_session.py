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


def get_session_region(session: boto3.Session) -> str:
    """
    Get the region for the session, with fallback to us-east-1
    
    Args:
        session: boto3 Session object
        
    Returns:
        Region name string
    """
    # Try to get region from session
    region = session.region_name
    
    # Fallback to us-east-1 if no region specified
    if not region:
        region = 'us-east-1'
    
    return region


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
        # Get region from session or use default
        region = get_session_region(session)
        ec2 = session.client('ec2', region_name=region)
        
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