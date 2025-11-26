"""EC2 instance scanning for IMDSv2 status"""

import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass
from typing import List, Optional

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