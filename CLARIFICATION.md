# EC2 IMDSv2 Enforcement Tool - Clarification Document

## Purpose
Create a Python CLI tool that enables IMDSv2 enforcement on EC2 instances across all enabled AWS regions for a given AWS account profile.

## Core Requirements (Confirmed from User Request)

### Input
- **AWS Profile**: Command-line argument to specify which AWS configuration profile to use
- **Scope**: All enabled regions in the target AWS account
- **Target**: All EC2 instances that do not have IMDSv2 enforcement enabled

### Processing
- Walk through all enabled AWS regions
- Detect EC2 instances where `HttpTokens` is not set to `required`
- Modify instance metadata options to set `HttpTokens='required'`

### Key AWS API Operations
- `describe_regions()`: Get list of enabled regions
- `describe_instances()`: List EC2 instances in each region
- `modify_instance_metadata_options()`: Enable IMDSv2 enforcement with `HttpTokens='required'`

## Technical Considerations

### Instance States
- IMDSv2 enforcement can be applied to both running and stopped instances
- For stopped instances: changes apply when instance starts
- For running instances: API returns "pending" state, then transitions to "applied"

### Region Discovery
The tool must:
1. Use `describe_regions()` to get all regions for the account
2. Only process regions that are enabled/available (OptInStatus check)
3. Handle regions where the account may not have access

## Confirmed User Requirements

### 1. Dry-Run and Confirmation ✓
**Decision**: Two-phase approach
- **Phase 1 (Scan)**: Scan all regions and instances, report what would be changed
- **Phase 2 (Apply)**: Ask for user confirmation, then apply changes if confirmed

### 2. Instance Filtering ✓
**Decision**: Process all instances regardless of state
- Include running, stopped, terminated, pending, shutting-down, stopping instances
- No filtering by tags or state - comprehensive scan

### 3. Error Handling Strategy ✓
**Decision**: Log errors but continue processing
- Errors will be logged with instance/region details
- Processing continues to remaining instances/regions
- Final summary includes error count and details

### 4. Output and Logging ✓
**Decision**: Detailed output level
- Show each instance ID being processed
- Display region being scanned
- Show current IMDSv2 status and new status after modification
- Include summary at the end with counts

### 5. Performance ✓
**Decision**: Sequential processing
- Process regions one at a time
- Process instances within each region sequentially
- Simpler to debug and provides clearer output flow

## Implementation Specifications

### CLI Interface
```bash
# Basic usage
python ec2_enable_imdsv2.py --profile <profile-name>

# Example
python ec2_enable_imdsv2.py --profile production
```

### Required AWS Permissions
The AWS profile must have the following IAM permissions:
- `ec2:DescribeRegions`
- `ec2:DescribeInstances`
- `ec2:ModifyInstanceMetadataOptions`

### Error Handling Rules
Following "Fail Fast and Loud" principle with modifications:
- API call failures: Log error, continue to next resource
- Authentication failures: Fail immediately (cannot proceed)
- Permission errors: Log error, continue to next resource
- Invalid profile: Fail immediately (cannot proceed)

### Output Format

**Phase 1 - Scan Output:**
```
Scanning AWS Account using profile: production
================================================================================

Region: us-east-1
  Found 5 EC2 instances
  Instance i-1234567890abcdef0 [running]: IMDSv2 NOT enforced (HttpTokens: optional)
  Instance i-abcdef1234567890a [stopped]: IMDSv2 NOT enforced (HttpTokens: optional)
  Instance i-fedcba0987654321b [running]: IMDSv2 already enforced ✓
  ...

Region: us-west-2
  Found 3 EC2 instances
  Instance i-9876543210fedcba0 [running]: IMDSv2 NOT enforced (HttpTokens: optional)
  ...

================================================================================
Scan Summary:
  Total regions scanned: 16
  Total instances found: 45
  Instances requiring IMDSv2 enforcement: 23
  Instances already compliant: 22
  Errors encountered: 0

Continue with enabling IMDSv2 enforcement? (yes/no):
```

**Phase 2 - Apply Output:**
```
Enabling IMDSv2 enforcement...
================================================================================

Region: us-east-1
  ✓ Instance i-1234567890abcdef0: IMDSv2 enforcement enabled (state: applied)
  ✓ Instance i-abcdef1234567890a: IMDSv2 enforcement enabled (state: pending)
  
Region: us-west-2
  ✓ Instance i-9876543210fedcba0: IMDSv2 enforcement enabled (state: applied)
  ✗ Instance i-xyz123abc456def78: Failed - InsufficientInstanceCapacity
  ...

================================================================================
Final Summary:
  Instances successfully updated: 22
  Instances failed to update: 1
  Total time: 45.3 seconds

Detailed error log:
  - us-west-2/i-xyz123abc456def78: InsufficientInstanceCapacity - The instance is in an invalid state
```

### Technical Architecture

The tool will be structured with the following components:

1. **CLI Module** (`cli.py`): Argument parsing and main entry point
2. **AWS Session Manager** (`aws_session.py`): Profile-based session initialization
3. **Region Scanner** (`region_scanner.py`): Region discovery and enumeration
4. **Instance Scanner** (`instance_scanner.py`): EC2 instance discovery and IMDSv2 status check
5. **Instance Modifier** (`instance_modifier.py`): Apply IMDSv2 enforcement modifications
6. **Reporter** (`reporter.py`): Output formatting and summary generation
7. **Error Handler** (`error_handler.py`): Error logging and tracking

### Project Structure
```
ec2-enable-imdsv2/
├── README.md
├── requirements.txt
├── setup.py
├── ec2_enable_imdsv2/
│   ├── __init__.py
│   ├── cli.py
│   ├── aws_session.py
│   ├── region_scanner.py
│   ├── instance_scanner.py
│   ├── instance_modifier.py
│   ├── reporter.py
│   └── error_handler.py
└── tests/
    ├── __init__.py
    └── test_*.py
```

## Assumptions

1. The AWS profile specified has appropriate permissions as listed above
2. The tool will NOT modify other metadata options (only `HttpTokens`)
3. The tool will check for instances in all states including terminated
4. API rate limits are handled by boto3's built-in retry mechanism
5. The tool requires Python 3.8 or higher
6. The tool will use boto3 and botocore for AWS API interactions

## Non-Functional Requirements

### Performance
- Should complete scanning 100 instances across 10 regions within 2-3 minutes
- Sequential processing acceptable for clarity and debugging

### Reliability
- Must handle transient API failures gracefully
- Must not corrupt or partially modify instance metadata
- Must provide accurate reporting of successes and failures

### Usability
- Clear, actionable error messages
- Progress indication during long-running operations
- User confirmation before making any changes

### Security
- No hardcoded credentials
- Use AWS profile-based authentication only
- No sensitive information in logs or output