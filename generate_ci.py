#!/usr/bin/env python3
"""
CI Workflow Generator for Godot Universal Build System

Generates a GitHub Actions workflow YAML based on the current build system configuration.
- By default, uses the template from build-documentation-universal.yml
- On first run, should be invoked after running the configuration wizard
- Writes the workflow to .github/workflows/build-documentation-universal.yml

Usage:
    python godot-ci-build-system/generate_ci.py

Optionally, pass --config <path> to use a specific build_config.json
"""
import sys
import shutil
from pathlib import Path
import argparse

DEFAULT_TEMPLATE = Path(__file__).parent / "ci-template/github/.github/workflows/build-documentation-universal.yml"
OUTPUT_PATH = Path(__file__).parent.parent / ".github/workflows/build-documentation-universal.yml"


def main():
    parser = argparse.ArgumentParser(description="Generate CI workflow for Godot Universal Build System")
    parser.add_argument('--config', type=Path, help='Path to build_config.json (optional)')
    parser.add_argument('--output', type=Path, default=OUTPUT_PATH, help='Output path for workflow YAML')
    args = parser.parse_args()

    # Use the default template as the base
    if not DEFAULT_TEMPLATE.exists():
        print(f"❌ Default workflow template not found: {DEFAULT_TEMPLATE}")
        sys.exit(1)

    # Optionally, could parse build_config.json and customize the workflow here
    # For now, just copy the template
    shutil.copy(DEFAULT_TEMPLATE, args.output)
    print(f"✅ CI workflow generated at {args.output}")

if __name__ == "__main__":
    main()
