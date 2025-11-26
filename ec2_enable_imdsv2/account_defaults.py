"""Account-level IMDS defaults management for EC2 IMDSv2 enforcement tool"""

import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from .error_handler import error_tracker


@dataclass
class AccountDefaultResult:
    """Result of an account-level default modification"""
    region: str
    success: bool
    previous_http_tokens: Optional[str] = None
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        """Format result for display"""
        if self.success:
            prev = self.previous_http_tokens if self.previous_http_tokens else "not set"
            return f"✓ Region {self.region}: Account defaults updated (was: {prev}, now: required)"
        else:
            return f"✗ Region {self.region}: Failed - {self.error_message}"


def get_account_metadata_defaults(session: boto3.Session, region: str) -> Optional[dict]:
    """
    Get current account-level metadata defaults for a region
    
    Args:
        session: boto3 Session object
        region: Region name
        
    Returns:
        Dictionary with current defaults or None if error
    """
    try:
        ec2 = session.client('ec2', region_name=region)
        response = ec2.get_instance_metadata_defaults()
        
        return response.get('AccountLevel', {})
        
    except ClientError as e:
        error_tracker.log_error('account_defaults', e, region=region)
        return None


def modify_account_metadata_defaults(
    session: boto3.Session,
    region: str
) -> AccountDefaultResult:
    """
    Modify account-level metadata defaults to require IMDSv2
    
    Args:
        session: boto3 Session object
        region: Region name
        
    Returns:
        AccountDefaultResult object with operation status
    """
    try:
        ec2 = session.client('ec2', region_name=region)
        
        # Get current defaults to report what changed
        current_defaults = get_account_metadata_defaults(session, region)
        previous_http_tokens = None
        if current_defaults:
            previous_http_tokens = current_defaults.get('HttpTokens')
        
        # Modify account defaults to require IMDSv2
        response = ec2.modify_instance_metadata_defaults(
            HttpTokens='required'
        )
        
        success = response.get('Return', False)
        
        return AccountDefaultResult(
            region=region,
            success=success,
            previous_http_tokens=previous_http_tokens
        )
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        
        error_tracker.log_error(
            'account_defaults',
            e,
            region=region
        )
        
        return AccountDefaultResult(
            region=region,
            success=False,
            error_message=f"{error_code}: {error_msg}"
        )


def modify_account_defaults_parallel(
    session: boto3.Session,
    regions: List[str]
) -> List[AccountDefaultResult]:
    """
    Modify account-level metadata defaults for multiple regions in parallel
    
    Args:
        session: boto3 Session object
        regions: List of region names
        
    Returns:
        List of AccountDefaultResult objects
    """
    results = []
    max_workers = min(len(regions), 10)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_region = {
            executor.submit(modify_account_metadata_defaults, session, region): region
            for region in regions
        }
        
        for future in as_completed(future_to_region):
            region = future_to_region[future]
            try:
                result = future.result()
                results.append(result)
                # Print progress
                print(f"  {result}")
            except Exception as e:
                error_tracker.log_error('account_defaults_parallel', e, region=region)
                results.append(AccountDefaultResult(
                    region=region,
                    success=False,
                    error_message=str(e)
                ))
    
    return results


def check_account_defaults_parallel(
    session: boto3.Session,
    regions: List[str]
) -> dict:
    """
    Check current account-level metadata defaults for multiple regions in parallel
    
    Args:
        session: boto3 Session object
        regions: List of region names
        
    Returns:
        Dictionary mapping region to current HttpTokens value
    """
    region_defaults = {}
    max_workers = min(len(regions), 10)
    
    def check_region(region: str) -> tuple:
        defaults = get_account_metadata_defaults(session, region)
        http_tokens = None
        if defaults:
            http_tokens = defaults.get('HttpTokens')
        return region, http_tokens
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_region = {
            executor.submit(check_region, region): region
            for region in regions
        }
        
        for future in as_completed(future_to_region):
            try:
                region, http_tokens = future.result()
                region_defaults[region] = http_tokens
            except Exception as e:
                region = future_to_region[future]
                error_tracker.log_error('check_account_defaults', e, region=region)
                region_defaults[region] = None
    
    return region_defaults


def get_account_defaults_summary(results: List[AccountDefaultResult]) -> dict:
    """
    Get summary statistics for account defaults modification results
    
    Args:
        results: List of AccountDefaultResult objects
        
    Returns:
        Dictionary with summary statistics
    """
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful
    
    # Collect error details
    errors = [
        f"{r.region}: {r.error_message}"
        for r in results if not r.success
    ]
    
    return {
        'total': total,
        'successful': successful,
        'failed': failed,
        'error_details': errors
    }


def get_account_defaults_stats(region_defaults: dict) -> dict:
    """
    Get statistics about account defaults across regions
    
    Args:
        region_defaults: Dictionary mapping region to HttpTokens value
        
    Returns:
        Dictionary with statistics
    """
    total = len(region_defaults)
    required = sum(1 for v in region_defaults.values() if v == 'required')
    optional = sum(1 for v in region_defaults.values() if v == 'optional')
    not_set = sum(1 for v in region_defaults.values() if v is None or v == 'no-preference')
    
    return {
        'total': total,
        'required': required,
        'optional': optional,
        'not_set': not_set,
        'needs_update': optional + not_set
    }