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