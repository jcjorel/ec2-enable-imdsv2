"""Error handling and tracking for EC2 IMDSv2 enforcement tool"""

from dataclasses import dataclass
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