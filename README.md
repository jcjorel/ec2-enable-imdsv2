# EC2 IMDSv2 Enforcement Tool

A Python CLI tool that enables IMDSv2 (Instance Metadata Service Version 2) enforcement on EC2 instances across all enabled AWS regions in your account.

## Overview

This tool helps you secure your AWS EC2 instances by enforcing the use of IMDSv2, which provides additional security through session-oriented requests. The tool will:

1. **Scan** all enabled regions in parallel (6-10x faster than sequential)
2. **Check** both existing instances AND account-level defaults
3. **Identify** instances and regions that need IMDSv2 enforcement
4. **Report** comprehensive findings and ask for confirmation
5. **Apply** IMDSv2 enforcement to instances and/or account defaults upon your approval

## Why IMDSv2?

IMDSv2 provides enhanced security for accessing instance metadata:
- **Session-oriented**: Requires token-based authentication
- **Prevents SSRF attacks**: Mitigates Server-Side Request Forgery vulnerabilities
- **AWS Best Practice**: Recommended security configuration for all EC2 instances

For more information, see [AWS Documentation on IMDSv2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html).

## Features

- ✅ **Parallel Scanning**: Scans all enabled regions simultaneously (6-10x faster)
- ✅ **Dual Enforcement**: Handles both existing instances AND account-level defaults
- ✅ **Integrated Workflow**: Single command checks and updates everything
- ✅ **Safe Two-Phase Approach**: Scan first, then apply changes with separate confirmations
- ✅ **Detailed Reporting**: Shows instance status and account defaults per region
- ✅ **Error Resilience**: Continues processing even if some operations fail
- ✅ **Clear Output**: Real-time progress indicators and comprehensive summaries
- ✅ **AWS Profile Support**: Automatically uses profile region or defaults to us-east-1

## Prerequisites

- **Python**: 3.8 or higher
- **AWS CLI**: Configured with profiles
- **AWS Credentials**: Valid credentials with required permissions
- **IAM Permissions**:
  - `ec2:DescribeRegions` (required)
  - `ec2:DescribeInstances` (required)
  - `ec2:ModifyInstanceMetadataOptions` (required for existing instances)
  - `ec2:GetInstanceMetadataDefaults` (required for checking account defaults)
  - `ec2:ModifyInstanceMetadataDefaults` (required for setting account defaults)

## Installation

### Option 1: Install from source

```bash
# Clone the repository
git clone <repository-url>
cd ec2-enable-imdsv2

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Option 2: Install dependencies only

```bash
pip install boto3>=1.34.0 botocore>=1.34.0
```

## Usage

### Basic Command

```bash
ec2-enable-imdsv2 --profile <your-aws-profile-name>
```

### Example

```bash
# Using production AWS profile
ec2-enable-imdsv2 --profile production

# Using development AWS profile  
ec2-enable-imdsv2 --profile dev-account
```

### Help

```bash
ec2-enable-imdsv2 --help
```

## How It Works

### Phase 1: Parallel Scan

The tool scans all regions simultaneously for instances AND account defaults:

```
Scanning AWS Account using profile: production
Account ID: 123456789012
================================================================================

Scanning 16 regions in parallel...
  - Checking instances
  - Checking account-level defaults

  ✓ Scanned us-east-1: 5 instance(s) found
  ✓ Scanned us-west-2: 3 instance(s) found
  ✓ Scanned eu-west-1: 2 instance(s) found
  ... (all regions scan simultaneously)

Checking account-level defaults...
  ✓ Account defaults checked

Scan Results:
================================================================================

Region: eu-west-1
  Found 2 EC2 instances
  Instance i-abc123 [running]: IMDSv2 NOT enforced (HttpTokens: optional)

Region: us-east-1
  Found 5 EC2 instances
  Instance i-1234567890abcdef0 [running]: IMDSv2 NOT enforced (HttpTokens: optional)
  Instance i-fedcba0987654321b [running]: IMDSv2 already enforced ✓

Region: us-west-2
  Found 3 EC2 instances
  Instance i-xyz789 [running]: IMDSv2 NOT enforced (HttpTokens: optional)

================================================================================
Scan Summary:
  Total regions scanned: 16
  Total instances found: 10
  Instances requiring IMDSv2 enforcement: 3
  Instances already compliant: 7

Account-Level Defaults (for new instances):
  Regions with 'required': 2
  Regions with 'optional': 8
  Regions not set: 6
  Regions needing update: 14

  Errors encountered: 0

Enable IMDSv2 enforcement on 3 existing instance(s)? (yes/no): yes

Set account-level defaults to 'required' in 14 region(s)? (yes/no): yes
```

### Phase 2: Apply Instance Changes

```
Enabling IMDSv2 enforcement...
================================================================================

Region: eu-west-1
  ✓ Instance i-abc123: IMDSv2 enforcement enabled (state: applied)

Region: us-east-1
  ✓ Instance i-1234567890abcdef0: IMDSv2 enforcement enabled (state: applied)

Region: us-west-2
  ✓ Instance i-xyz789: IMDSv2 enforcement enabled (state: applied)

================================================================================
Final Summary:
  Instances successfully updated: 3
  Instances failed to update: 0
  Total time: 12.5 seconds

✓ All instances successfully updated with IMDSv2 enforcement!
```

### Phase 3: Apply Account Defaults

```
Setting Account-Level Defaults...
================================================================================

ℹ This sets defaults for NEW instances only. Existing instances are not affected.

  ✓ Region ap-northeast-1: Account defaults updated (was: optional, now: required)
  ✓ Region ap-south-1: Account defaults updated (was: not set, now: required)
  ✓ Region eu-central-1: Account defaults updated (was: optional, now: required)
  ... (all regions update in parallel)

================================================================================
Account Defaults Summary:
  Regions successfully updated: 14
  Regions failed to update: 0

✓ All regions successfully configured with IMDSv2 account defaults!
ℹ New instances will now require IMDSv2 by default.
```

## Understanding the Output

### Instance States

- **applied**: Change has been applied immediately (common for stopped instances)
- **pending**: Change is being applied (common for running instances)

### Status Indicators

- ✓ Success
- ✗ Error
- ⚠ Warning

### HttpTokens Values

- **required**: IMDSv2 is enforced (goal state)
- **optional**: IMDSv2 is available but not required (needs update)
- **not set**: No explicit setting (treated as optional, needs update)

## Error Handling

The tool is designed to continue processing even when errors occur:

- **Logged Errors**: All errors are logged with instance/region details
- **Continued Processing**: One failure won't stop processing of other instances
- **Final Summary**: Detailed error report at the end

Example error output:

```
Region: us-west-2
  ✓ Instance i-abc123: IMDSv2 enforcement enabled (state: applied)
  ✗ Instance i-def456: Failed - InvalidInstanceID.NotFound

================================================================================
Final Summary:
  Instances successfully updated: 22
  Instances failed to update: 1
  Total time: 45.3 seconds

Detailed error log:
  - us-west-2/i-def456: InvalidInstanceID.NotFound - The instance may have been terminated
```

## Security Best Practices

1. **Use IAM Roles**: Prefer IAM roles over access keys when possible
2. **Least Privilege**: Grant only required permissions
3. **Audit Changes**: Review the scan results before confirming
4. **Test First**: Test on a non-production account first
5. **Backup Configuration**: Document current settings before making changes

## IAM Policy Example

Complete permissions (for both instances and account defaults):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeRegions",
        "ec2:DescribeInstances",
        "ec2:ModifyInstanceMetadataOptions",
        "ec2:GetInstanceMetadataDefaults",
        "ec2:ModifyInstanceMetadataDefaults"
      ],
      "Resource": "*"
    }
  ]
}
```

Minimum permissions (instances only, no account defaults):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeRegions",
        "ec2:DescribeInstances",
        "ec2:ModifyInstanceMetadataOptions"
      ],
      "Resource": "*"
    }
  ]
}
```

## Troubleshooting

### Profile Not Found

```
✗ Error: AWS profile 'production' not found
  Available profiles can be listed with: aws configure list-profiles
  Configure a new profile with: aws configure --profile production
```

**Solution**: Configure the AWS profile or use an existing one.

### Missing Permissions

```
⚠ Warning: Missing ec2:DescribeRegions permission
  This tool requires the following IAM permissions:
    - ec2:DescribeRegions
    - ec2:DescribeInstances
    - ec2:ModifyInstanceMetadataOptions
```

**Solution**: Add required permissions to your IAM user/role.

### No Enabled Regions

```
✗ No enabled regions found. Cannot proceed.
```

**Solution**: Ensure your AWS account has at least one enabled region.

### Instance Modification Failures

Common reasons for modification failures:
- **InvalidInstanceID.NotFound**: Instance was terminated
- **IncorrectInstanceState**: Instance is in a transitional state
- **UnauthorizedOperation**: Missing required permissions

**Solution**: Review the error message and retry if appropriate.

## What Gets Modified

### Existing Instances
- Sets `HttpTokens='required'` on each instance
- Applies to running, stopped, and terminated instances
- Changes take effect immediately (or on next start for stopped instances)

### Account-Level Defaults
- Sets `HttpTokens='required'` at account level per region
- Applies ONLY to NEW instances launched after the change
- Existing instances are NOT affected by account defaults

### Both Changes
You can choose to apply:
- Both changes (complete IMDSv2 enforcement)
- Only instance changes
- Only account defaults
- Neither (just scan)

## Project Structure

```
ec2-enable-imdsv2/
├── README.md                      # This file
├── CLARIFICATION.md              # Requirements clarification
├── TECHNICAL_PLAN.md             # Technical architecture
├── IMPLEMENTATION_GUIDE.md       # Detailed implementation guide
├── requirements.txt              # Python dependencies
├── setup.py                      # Package configuration
├── ec2_enable_imdsv2/           # Main package
│   ├── __init__.py
│   ├── cli.py                   # CLI entry point
│   ├── aws_session.py          # AWS session management
│   ├── region_scanner.py       # Region discovery
│   ├── instance_scanner.py     # Instance scanning
│   ├── instance_modifier.py    # Instance metadata modification
│   ├── account_defaults.py     # Account-level defaults management
│   ├── reporter.py             # Output formatting
│   └── error_handler.py        # Error tracking
└── tests/                       # Test suite
    └── ...
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run with coverage
pytest --cov=ec2_enable_imdsv2 tests/
```

### Code Style

The project follows PEP 8 guidelines. Format code with:

```bash
black ec2_enable_imdsv2/
flake8 ec2_enable_imdsv2/
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Open an issue on GitHub
- Check the [AWS IMDSv2 Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html)
- Review the [TECHNICAL_PLAN.md](TECHNICAL_PLAN.md) for architecture details

## Acknowledgments

- AWS Documentation for IMDSv2 best practices
- Boto3 team for the AWS SDK for Python

## Changelog

### Version 1.0.0 (Current Release)
- Parallel region scanning (6-10x faster)
- Complete scan and modification workflow for instances
- Account-level IMDS defaults management
- Support for all enabled AWS regions
- Automatic region detection from profile
- Interactive separate confirmations for instances and account defaults
- Detailed progress indicators and error reporting
- Comprehensive error handling

## Related Resources

- [AWS IMDSv2 Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html)
- [IMDSv2 Transition Guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-metadata-transition-to-version-2.html)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [AWS Security Best Practices](https://aws.amazon.com/security/security-resources/)