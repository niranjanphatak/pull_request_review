#!/usr/bin/env python3
"""
Setup DynamoDB Tables for PR Review System

This script creates the necessary DynamoDB tables for the PR review system.
Run this before using DynamoDB as your database backend.

Usage:
    python scripts/setup_dynamodb_tables.py

Environment variables:
    DYNAMODB_REGION - AWS region (default: us-east-1)
    DYNAMODB_TABLE_PREFIX - Table name prefix (default: pr_review)
    AWS_ACCESS_KEY_ID - AWS access key (optional, uses default credential chain if not set)
    AWS_SECRET_ACCESS_KEY - AWS secret key (optional, uses default credential chain if not set)
    DYNAMODB_ENDPOINT_URL - DynamoDB endpoint (optional, for local DynamoDB)
"""

import boto3
from botocore.exceptions import ClientError
import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config


def create_sessions_table(dynamodb, table_name):
    """Create sessions table"""
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'session_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'session_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'timestamp-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            Tags=[
                {
                    'Key': 'Application',
                    'Value': 'PR-Review-System'
                }
            ]
        )

        # Wait for table to be created
        table.wait_until_exists()
        print(f"✅ Created table: {table_name}")

        # Enable TTL on the ttl attribute
        dynamodb_client = boto3.client('dynamodb', **get_client_config())
        dynamodb_client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )
        print(f"   ✅ Enabled TTL for {table_name}")

        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False


def create_snapshots_table(dynamodb, table_name):
    """Create statistics snapshots table"""
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'snapshot_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'snapshot_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'snapshot_type',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'type-timestamp-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'snapshot_type',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            Tags=[
                {
                    'Key': 'Application',
                    'Value': 'PR-Review-System'
                }
            ]
        )

        table.wait_until_exists()
        print(f"✅ Created table: {table_name}")

        # Enable TTL
        dynamodb_client = boto3.client('dynamodb', **get_client_config())
        dynamodb_client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )
        print(f"   ✅ Enabled TTL for {table_name}")

        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False


def create_prompts_table(dynamodb, table_name):
    """Create prompt versions table"""
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'prompt_id',
                    'KeyType': 'HASH'  # Partition key (stage#version)
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'prompt_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'stage',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'stage-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'stage',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            Tags=[
                {
                    'Key': 'Application',
                    'Value': 'PR-Review-System'
                }
            ]
        )

        table.wait_until_exists()
        print(f"✅ Created table: {table_name}")

        # Enable TTL
        dynamodb_client = boto3.client('dynamodb', **get_client_config())
        dynamodb_client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )
        print(f"   ✅ Enabled TTL for {table_name}")

        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False


def create_onboarding_table(dynamodb, table_name):
    """Create onboarding table"""
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'onboarding_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'onboarding_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            Tags=[
                {
                    'Key': 'Application',
                    'Value': 'PR-Review-System'
                }
            ]
        )

        table.wait_until_exists()
        print(f"✅ Created table: {table_name}")

        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False


def create_prompt_candidates_table(dynamodb, table_name):
    """Create prompt candidates table"""
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'candidate_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'candidate_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            Tags=[
                {
                    'Key': 'Application',
                    'Value': 'PR-Review-System'
                }
            ]
        )

        table.wait_until_exists()
        print(f"✅ Created table: {table_name}")

        # Enable TTL
        dynamodb_client = boto3.client('dynamodb', **get_client_config())
        dynamodb_client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )
        print(f"   ✅ Enabled TTL for {table_name}")

        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False


def create_analysis_reports_table(dynamodb, table_name):
    """Create analysis reports table"""
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'report_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'report_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            Tags=[
                {
                    'Key': 'Application',
                    'Value': 'PR-Review-System'
                }
            ]
        )

        table.wait_until_exists()
        print(f"✅ Created table: {table_name}")

        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False


def get_client_config():
    """Get boto3 client configuration"""
    config = Config.get_dynamodb_config()

    client_config = {
        'region_name': config.get('region_name', 'us-east-1')
    }

    if config.get('aws_access_key_id') and config.get('aws_secret_access_key'):
        client_config['aws_access_key_id'] = config['aws_access_key_id']
        client_config['aws_secret_access_key'] = config['aws_secret_access_key']

    if config.get('endpoint_url'):
        client_config['endpoint_url'] = config['endpoint_url']

    return client_config


def main():
    """Main setup function"""
    print("=" * 60)
    print("DynamoDB Tables Setup for PR Review System")
    print("=" * 60)
    print()

    config = Config.get_dynamodb_config()
    table_prefix = config.get('table_prefix', 'pr_review')

    print(f"Configuration:")
    print(f"  Region: {config.get('region_name', 'us-east-1')}")
    print(f"  Table Prefix: {table_prefix}")
    if config.get('endpoint_url'):
        print(f"  Endpoint URL: {config['endpoint_url']} (Local DynamoDB)")
    print()

    # Create DynamoDB resource
    try:
        dynamodb = boto3.resource('dynamodb', **get_client_config())
    except Exception as e:
        print(f"❌ Failed to connect to DynamoDB: {e}")
        print()
        print("Please check your AWS credentials and configuration.")
        return 1

    # Create tables
    print("Creating tables...")
    print()

    results = []

    # Sessions table
    results.append(create_sessions_table(
        dynamodb,
        f"{table_prefix}_sessions"
    ))

    # Snapshots table
    results.append(create_snapshots_table(
        dynamodb,
        f"{table_prefix}_snapshots"
    ))

    # Prompts table
    results.append(create_prompts_table(
        dynamodb,
        f"{table_prefix}_prompts"
    ))

    # Onboarding table
    results.append(create_onboarding_table(
        dynamodb,
        f"{table_prefix}_onboarding"
    ))

    # Prompt candidates table
    results.append(create_prompt_candidates_table(
        dynamodb,
        f"{table_prefix}_prompt_candidates"
    ))

    # Analysis reports table
    results.append(create_analysis_reports_table(
        dynamodb,
        f"{table_prefix}_analysis_reports"
    ))

    print()
    print("=" * 60)

    if all(results):
        print("✅ All tables created successfully!")
        print()
        print("Next steps:")
        print("  1. Set DATABASE_TYPE=dynamodb in your .env file")
        print("  2. Restart your application")
        print()
        return 0
    else:
        print("⚠️  Some tables failed to create. Check the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
