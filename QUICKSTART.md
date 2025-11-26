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
1. ✅ Scan all your enabled regions in parallel (super fast!)
2. 📊 Check both instances AND account-level defaults
3. 📋 Show you comprehensive status for both
4. ❓ Ask for separate confirmations (instances and account defaults)
5. 🔧 Apply the changes you confirm
6. 📈 Show you detailed results

## Example Session

```bash
$ ec2-enable-imdsv2 --profile production

Scanning AWS Account using profile: production
Account ID: 123456789012
================================================================================

Scanning 16 regions in parallel...
  - Checking instances
  - Checking account-level defaults

  ✓ Scanned us-east-1: 5 instance(s) found
  ✓ Scanned us-west-2: 3 instance(s) found
  ✓ Scanned eu-west-1: 2 instance(s) found
  ... (all regions complete quickly)

Checking account-level defaults...
  ✓ Account defaults checked

Scan Results:
================================================================================

Region: eu-west-1
  Found 2 EC2 instances
  Instance i-abc123 [running]: IMDSv2 NOT enforced (HttpTokens: optional)

Region: us-east-1
  Found 5 EC2 instances
  Instance i-def456 [stopped]: IMDSv2 already enforced ✓
  Instance i-xyz789 [running]: IMDSv2 NOT enforced (HttpTokens: optional)

Region: us-west-2
  Found 3 EC2 instances
  Instance i-123abc [running]: IMDSv2 NOT enforced (HttpTokens: optional)

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

Enabling IMDSv2 enforcement...
================================================================================

Region: eu-west-1
  ✓ Instance i-abc123: IMDSv2 enforcement enabled (state: applied)

Region: us-east-1
  ✓ Instance i-xyz789: IMDSv2 enforcement enabled (state: applied)

Region: us-west-2
  ✓ Instance i-123abc: IMDSv2 enforcement enabled (state: applied)

================================================================================
Final Summary:
  Instances successfully updated: 3
  Instances failed to update: 0
  Total time: 8.5 seconds

✓ All instances successfully updated with IMDSv2 enforcement!

Setting Account-Level Defaults...
================================================================================

ℹ This sets defaults for NEW instances only. Existing instances are not affected.

  ✓ Region ap-northeast-1: Account defaults updated (was: optional, now: required)
  ✓ Region ap-south-1: Account defaults updated (was: not set, now: required)
  ✓ Region eu-central-1: Account defaults updated (was: optional, now: required)
  ... (updates complete in parallel)

================================================================================
Account Defaults Summary:
  Regions successfully updated: 14
  Regions failed to update: 0

✓ All regions successfully configured with IMDSv2 account defaults!
ℹ New instances will now require IMDSv2 by default.
```

## What Just Happened?

The tool:
- ✅ Scanned all enabled regions in parallel (super fast!)
- ✅ Checked both existing instances AND account-level defaults
- ✅ Found instances without IMDSv2 enforcement
- ✅ Found regions needing account-level defaults
- ✅ Asked for separate confirmations
- ✅ Updated existing instance metadata to require IMDSv2
- ✅ Set account defaults so NEW instances require IMDSv2
- ✅ Showed you comprehensive results

**Result**: Complete IMDSv2 enforcement for your AWS account!

## What If I Want to Just Check?

Just say "no" to both confirmations:

```
Enable IMDSv2 enforcement on 3 existing instance(s)? (yes/no): no

Set account-level defaults to 'required' in 14 region(s)? (yes/no): no

No changes to apply.
```

No changes will be made - it's just a scan!

You can also choose to apply only one type of change:
- Say "yes" to instances, "no" to account defaults → Only updates existing instances
- Say "no" to instances, "yes" to account defaults → Only sets defaults for new instances

## Required IAM Permissions

### For Complete Functionality (Recommended)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeRegions",
      "ec2:DescribeInstances",
      "ec2:ModifyInstanceMetadataOptions",
      "ec2:GetInstanceMetadataDefaults",
      "ec2:ModifyInstanceMetadataDefaults"
    ],
    "Resource": "*"
  }]
}
```

### For Instances Only (Minimum)

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
- ✅ Parallel scanning for speed (6-10x faster)
- ✅ Two-phase approach (scan first, modify after confirmations)
- ✅ Separate confirmations for instances vs account defaults
- ✅ Shows exactly what will change before making changes
- ✅ Continues processing even if some operations fail
- ✅ Provides detailed error messages
- ✅ Never stores or logs credentials
- ✅ Only modifies HttpTokens settings (nothing else)
- ✅ Account defaults only affect NEW instances

## What is IMDSv2?

IMDSv2 (Instance Metadata Service Version 2) is a security enhancement for EC2 instances that:
- Requires session tokens for metadata access
- Prevents SSRF (Server-Side Request Forgery) attacks
- Is an AWS security best practice

## Two Types of Enforcement

1. **Existing Instances**: Modify running/stopped instances to require IMDSv2
2. **Account Defaults**: Set defaults so NEW instances require IMDSv2 automatically

This tool handles both in a single integrated workflow!

Learn more: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html