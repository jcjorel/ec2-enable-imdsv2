# EC2 IMDSv2 Enforcement Tool - Usage Guide

## Quick Start

### Installation

1. **Clone or download the project**:
```bash
cd /home/jcjorel/Devs/ec2-enable-imdsv2
```

2. **Create a virtual environment** (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install the tool**:
```bash
# Development installation (recommended for testing)
pip install -e .

# Or install dependencies only
pip install -r requirements.txt
```

### Basic Usage

Once installed, run the tool with your AWS profile:

```bash
ec2-enable-imdsv2 --profile <your-profile-name>
```

### Example Usage

```bash
# Using a specific AWS profile
ec2-enable-imdsv2 --profile production

# Get help
ec2-enable-imdsv2 --help

# Check version
ec2-enable-imdsv2 --version
```

## Prerequisites

### 1. AWS CLI Configuration

Ensure you have AWS CLI configured with at least one profile:

```bash
# Configure a new profile
aws configure --profile myprofile

# List existing profiles
aws configure list-profiles

# Test profile credentials
aws sts get-caller-identity --profile myprofile
```

### 2. IAM Permissions

Your AWS profile must have the following permissions:

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

### 3. Python Requirements

- Python 3.8 or higher
- boto3 >= 1.34.0
- botocore >= 1.34.0

## Running the Tool

### Step 1: Start the Tool

```bash
ec2-enable-imdsv2 --profile myprofile
```

### Step 2: Review Scan Results

The tool will scan all enabled regions and display:
- Total regions scanned
- Total instances found
- Instances needing IMDSv2 enforcement
- Instances already compliant

Example output:
```
Scanning AWS Account using profile: production
Account ID: 123456789012
================================================================================

Region: us-east-1
  Found 5 EC2 instances
  Instance i-1234567890abcdef0 [running]: IMDSv2 NOT enforced (HttpTokens: optional)
  Instance i-abcdef1234567890a [stopped]: IMDSv2 already enforced ✓

Region: us-west-2
  Found 3 EC2 instances
  ...

================================================================================
Scan Summary:
  Total regions scanned: 16
  Total instances found: 45
  Instances requiring IMDSv2 enforcement: 23
  Instances already compliant: 22
  Errors encountered: 0

Continue with enabling IMDSv2 enforcement on 23 instance(s)? (yes/no):
```

### Step 3: Confirm Changes

- Type `yes` or `y` to proceed with enabling IMDSv2
- Type `no` or `n` to cancel the operation

### Step 4: Review Results

After confirmation, the tool will:
- Enable IMDSv2 enforcement on each instance
- Display the result for each modification
- Show a final summary with success/failure counts

Example output:
```
Enabling IMDSv2 enforcement...
================================================================================

Region: us-east-1
  ✓ Instance i-1234567890abcdef0: IMDSv2 enforcement enabled (state: applied)
  ✓ Instance i-abcdef1234567890a: IMDSv2 enforcement enabled (state: pending)

Region: us-west-2
  ✓ Instance i-9876543210fedcba0: IMDSv2 enforcement enabled (state: applied)

================================================================================
Final Summary:
  Instances successfully updated: 23
  Instances failed to update: 0
  Total time: 45.3 seconds

✓ All instances successfully updated with IMDSv2 enforcement!
```

## Understanding the Output

### Instance States

- **applied**: Change has been immediately applied (common for stopped instances)
- **pending**: Change is being applied (common for running instances)

### Status Indicators

- ✓ = Success
- ✗ = Error
- ⚠ = Warning

### HttpTokens Values

- **required**: IMDSv2 is enforced (desired state)
- **optional**: IMDSv2 available but not required (needs update)
- **not set**: No explicit setting (treated as optional, needs update)

## Testing the Tool

### Test Without Making Changes

To test the tool without making actual changes:

1. Run the tool normally
2. Review the scan results
3. Answer `no` when prompted for confirmation
4. No changes will be made to your instances

### Test in a Non-Production Environment

**Strongly recommended** before running in production:

```bash
# Test with development account
ec2-enable-imdsv2 --profile dev-account

# Review results, confirm if satisfied
```

### Verify Changes

After running the tool, verify IMDSv2 is enforced:

```bash
# Using AWS CLI
aws ec2 describe-instances \
  --instance-ids i-1234567890abcdef0 \
  --query 'Reservations[0].Instances[0].MetadataOptions.HttpTokens' \
  --profile myprofile

# Expected output: "required"
```

Or use the AWS Console:
1. Go to EC2 → Instances
2. Select an instance
3. Go to Actions → Instance settings → Modify instance metadata options
4. Verify "IMDSv2" is set to "Required"

## Troubleshooting

### Common Issues

#### 1. Profile Not Found

```
✗ Error: AWS profile 'production' not found
  Available profiles can be listed with: aws configure list-profiles
```

**Solution**: Configure the profile or use an existing one:
```bash
aws configure --profile production
```

#### 2. Permission Denied

```
⚠ Warning: Missing ec2:DescribeRegions permission
```

**Solution**: Add required IAM permissions to your user/role.

#### 3. No Instances Found

```
Scan Summary:
  Total instances found: 0
```

**Possible Reasons**:
- No EC2 instances in the account
- Instances in regions not enabled for your account
- Permission issues preventing instance discovery

#### 4. Modification Failures

```
✗ Instance i-xyz123: Failed - InvalidInstanceID.NotFound
```

**Common Causes**:
- Instance was terminated between scan and modification
- Instance in invalid state (e.g., terminating)
- Insufficient permissions

### Getting Help

If you encounter issues:

1. Check the error message for specific guidance
2. Review the [README.md](README.md) for detailed documentation
3. Check AWS CloudTrail for API call details
4. Verify IAM permissions match requirements

## Advanced Usage

### Running Without Installation

If you prefer not to install the package:

```bash
# From project root directory
python -m ec2_enable_imdsv2.cli --profile myprofile
```

### Using with CI/CD

The tool returns exit codes for automation:
- **0**: Success (all instances updated or no updates needed)
- **1**: Partial failure (some instances failed to update)
- **130**: User cancelled (Ctrl+C)

Example in a script:
```bash
#!/bin/bash
ec2-enable-imdsv2 --profile production
if [ $? -eq 0 ]; then
    echo "IMDSv2 enforcement completed successfully"
else
    echo "IMDSv2 enforcement completed with errors"
    exit 1
fi
```

## Best Practices

1. **Test First**: Always test in non-production before production
2. **Review Scan**: Carefully review scan results before confirming
3. **Monitor After**: Check instance behavior after IMDSv2 enforcement
4. **Document Changes**: Keep records of when and what was changed
5. **Gradual Rollout**: Consider enabling by region or instance type first

## Uninstalling

To uninstall the tool:

```bash
# If installed with pip install -e .
pip uninstall ec2-enable-imdsv2

# Deactivate and remove virtual environment
deactivate
rm -rf venv
```

## Project Structure

```
ec2-enable-imdsv2/
├── README.md                          # Main documentation
├── USAGE.md                          # This file
├── CLARIFICATION.md                  # Requirements documentation
├── TECHNICAL_PLAN.md                 # Technical architecture
├── IMPLEMENTATION_GUIDE.md           # Implementation details
├── ARCHITECTURE_SUMMARY.md           # Architecture summary
├── requirements.txt                  # Python dependencies
├── setup.py                          # Package configuration
└── ec2_enable_imdsv2/               # Main package
    ├── __init__.py
    ├── cli.py                       # CLI entry point
    ├── aws_session.py              # AWS session management
    ├── region_scanner.py           # Region discovery
    ├── instance_scanner.py         # Instance scanning
    ├── instance_modifier.py        # Metadata modification
    ├── reporter.py                 # Output formatting
    └── error_handler.py            # Error tracking
```

## Support and Resources

- **AWS IMDSv2 Documentation**: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html
- **Boto3 Documentation**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- **AWS CLI Configuration**: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html