"""Setup configuration for ec2-enable-imdsv2"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ec2-enable-imdsv2",
    version="1.0.0",
    author="EC2 IMDSv2 Tool",
    description="Enable IMDSv2 enforcement on EC2 instances across all AWS regions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "boto3>=1.34.0",
        "botocore>=1.34.0",
    ],
    entry_points={
        "console_scripts": [
            "ec2-enable-imdsv2=ec2_enable_imdsv2.cli:main",
        ],
    },
)