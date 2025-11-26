# Quick Start Guide - EC2 IMDSv2 Enforcement Tool

## 5-Minute Setup

### Step 1: Install (30 seconds)

```bash
cd /home/jcjorel/Devs/ec2-enable-imdsv2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the tool
pip install -e .
```

### Step 2: Verify AWS Profile (15 seconds)

```bash
# List your AWS profiles
aws configure list-profiles

# Test your profile works
aws sts get-caller-identity --profile YOUR_PROFILE_NAME
```

### Step 3: Run the Tool (3-5 minutes)

```bash
# Replace YOUR_PROFILE_NAME with your actual profile
ec2-enable-imdsv2 --profile YOUR_PROFILE_NAME
```

That's it! The tool will:
1. ✅ Scan all your enabled regions
2. 📊 Show you which instances need IMDSv2 enforcement
3. ❓ Ask for your confirmation
4. 🔧 Apply the changes if you confirm
5. 📈 Show you the results

## Example Session

```bash
$ ec2-enable-imdsv2 --profile production

Scanning AWS Account using profile: production
Account ID: 123456789012
================================================================================

Region: us-east-1
  Found 5 EC2 instances
  Instance i-abc123 [running]: IMDSv2 NOT enforced (HttpTokens: optional)
  Instance i-def456 [stopped]: IMDSv2 already enforced ✓

Region: us-west-2
  Found 3 EC2 instances
  Instance i-xyz789 [running]: IMDSv2 NOT enforced (HttpTokens: optional)

================================================================================
Scan Summary:
  Total regions scanned: 16
  Total instances found: 8
  Instances requiring IMDSv2 enforcement: 2
  Instances already compliant: 6
  Errors encountered: 0

Continue with enabling IMDSv2 enforcement on 2 instance(s)? (yes/no): yes

Enabling IMDSv2 enforcement...
================================================================================

Region: us-east-1
  ✓ Instance i-abc123: IMDSv2 enforcement enabled (state: applied)

Region: us-west-2
  ✓ Instance i-xyz789: IMDSv2 enforcement enabled (state: applied)

================================================================================
Final Summary:
  Instances successfully updated: 2
  Instances failed to update: 0
  Total time: 12.3 seconds

✓ All instances successfully updated with IMDSv2 enforcement!
```

## What Just Happened?

The tool:
- ✅ Scanned all enabled regions in your AWS account
- ✅ Found instances without IMDSv2 enforcement
- ✅ Asked for your confirmation
- ✅ Updated instance metadata to require IMDSv2
- ✅ Showed you the results

## What If I Want to Just Check?

Just say "no" when asked for confirmation:

```
Continue with enabling IMDSv2 enforcement on 2 instance(s)? (yes/no): no
Operation cancelled by user
```

No changes will be made!

## Required IAM Permissions

Your AWS profile needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeRegions",
      "ec2:DescribeInstances",
      "ec2:ModifyInstanceMetadataOptions"
    ],
    "Resource": "*"
  }]
}
```

## Troubleshooting

### "Profile not found"
```bash
# Configure the profile
aws configure --profile YOUR_PROFILE_NAME
```

### "Permission denied"
Add the required IAM permissions (see above) to your AWS user/role.

### "Command not found: ec2-enable-imdsv2"
Make sure you activated the virtual environment:
```bash
source venv/bin/activate
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [USAGE.md](USAGE.md) for advanced usage and examples
- Review [TECHNICAL_PLAN.md](TECHNICAL_PLAN.md) to understand the architecture

## Getting Help

```bash
# Show help
ec2-enable-imdsv2 --help

# Show version
ec2-enable-imdsv2 --version
```

## Safety Features

The tool is designed to be safe:
- ✅ Two-phase approach (scan first, modify after confirmation)
- ✅ Shows you exactly what will change before making changes
- ✅ Continues processing even if some instances fail
- ✅ Provides detailed error messages
- ✅ Never stores or logs credentials
- ✅ Only modifies the HttpTokens setting (nothing else)

## What is IMDSv2?

IMDSv2 (Instance Metadata Service Version 2) is a security enhancement for EC2 instances that:
- Requires session tokens for metadata access
- Prevents SSRF (Server-Side Request Forgery) attacks
- Is an AWS security best practice

Learn more: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html