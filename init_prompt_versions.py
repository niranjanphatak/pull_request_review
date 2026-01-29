#!/usr/bin/env python3
"""
Initialize Prompt Versions Script

This script reads the prompt files from the prompts/ directory and stores them
in MongoDB with version tracking. Run this script after setting up the system
or whenever you update prompt files.

Usage:
  python init_prompt_versions.py
  python init_prompt_versions.py --version 1.1.0  # specify custom version
"""

import sys
import argparse
import os
from utils.database_factory import create_database


def extract_description_and_criteria(prompt_content: str) -> tuple:
    """
    Extract description and criteria from prompt content

    Returns:
        (description, criteria_list)
    """
    lines = prompt_content.split('\n')
    description = ""
    criteria = []

    in_focus_area = False

    for line in lines:
        stripped = line.strip()

        # Get the first line as description
        if not description and stripped and not stripped.startswith('#'):
            description = stripped

        # Extract criteria from Focus Areas section
        if '## Focus Areas:' in line or '## Focus:' in line:
            in_focus_area = True
            continue
        elif in_focus_area:
            if stripped.startswith('##') or stripped.startswith('**'):
                in_focus_area = False
            elif stripped.startswith('-'):
                criteria.append(stripped[1:].strip())

    if not description:
        description = "Code review analysis for quality assurance"

    return description, criteria


def init_prompts(version: str = "1.0.0"):
    """Initialize prompt versions in MongoDB"""
    print(f"\n{'='*80}")
    print(f"Initializing Prompt Versions - v{version}")
    print(f"{'='*80}\n")

    # Initialize Database connection (Factory)
    storage = create_database()

    if not storage.connected:
        print("❌ ERROR: Cannot connect to the database")
        print("   Make sure your configured database is accessible.")
        sys.exit(1)

    # Define prompt files
    prompt_files = {
        'architecture': 'prompts/architecture_compliance.txt',
        'security': 'prompts/security_review.txt',
        'bugs': 'prompts/bug_detection.txt',
        'style': 'prompts/style_optimization.txt',
        'performance': 'prompts/performance_optimization.txt',
        'tests': 'prompts/test_suggestions.txt'
    }

    initialized = 0

    for stage, filepath in prompt_files.items():
        if not os.path.exists(filepath):
            print(f"⚠️  WARNING: {filepath} not found, skipping {stage}")
            continue

        print(f"\n📝 Processing {stage} prompt...")

        # Read prompt content
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                prompt_content = f.read().strip()
        except Exception as e:
            print(f"❌ ERROR: Failed to read {filepath}: {e}")
            continue

        # Extract description and criteria
        description, criteria = extract_description_and_criteria(prompt_content)

        print(f"   Description: {description[:60]}...")
        print(f"   Criteria: {len(criteria)} items")

        # Check if version already exists
        existing = storage.get_prompt_version(stage, version)
        if existing:
            print(f"   ⚠️  Version {version} already exists for {stage}")
            print(f"   Deactivating old version...")
            storage.deactivate_prompt_version(stage, version)

        # Save to MongoDB
        prompt_id = storage.save_prompt_version(
            stage=stage,
            version=version,
            prompt_content=prompt_content,
            description=description,
            criteria=criteria
        )

        if prompt_id:
            print(f"   ✅ Saved: {stage} v{version}")
            print(f"   ID: {prompt_id}")
            initialized += 1
        else:
            print(f"   ❌ Failed to save {stage}")

    # Close connection
    storage.close()

    print(f"\n{'='*80}")
    print(f"✅ Initialization completed: {initialized}/{len(prompt_files)} prompts saved")
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='Initialize prompt versions in MongoDB')
    parser.add_argument('--version', default='1.0.0', help='Version string (e.g., 1.0.0, 1.1.0)')

    args = parser.parse_args()

    init_prompts(args.version)


if __name__ == '__main__':
    main()
