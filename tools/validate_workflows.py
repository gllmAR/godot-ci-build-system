#!/usr/bin/env python3
"""
Validate GitHub Actions workflow files
"""

import yaml
import sys
from pathlib import Path

def validate_workflow(workflow_file):
    """Validate a single workflow file"""
    try:
        with open(workflow_file, 'r') as f:
            workflow = yaml.safe_load(f)
        
        # Basic validation
        if 'name' not in workflow:
            return False, "Missing 'name' field"
        
        # Check for 'on' field (which YAML parses as True boolean)
        if 'on' not in workflow and True not in workflow:
            return False, "Missing 'on' field"
        
        if 'jobs' not in workflow:
            return False, "Missing 'jobs' field"
        
        # Check jobs have required fields
        for job_name, job_config in workflow['jobs'].items():
            if 'runs-on' not in job_config:
                return False, f"Job '{job_name}' missing 'runs-on'"
            
            if 'steps' not in job_config:
                return False, f"Job '{job_name}' missing 'steps'"
        
        return True, "Valid"
        
    except yaml.YAMLError as e:
        return False, f"YAML error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def main():
    """Main validation function"""
    workflows_dir = Path(__file__).parent.parent.parent / '.github' / 'workflows'
    
    print(f"Looking for workflows in: {workflows_dir}")
    
    if not workflows_dir.exists():
        print("❌ .github/workflows directory not found")
        return 1
    
    workflow_files = list(workflows_dir.glob('*.yml')) + list(workflows_dir.glob('*.yaml'))
    
    if not workflow_files:
        print("⚠️ No workflow files found")
        return 0
    
    print(f"🔍 Validating {len(workflow_files)} workflow files...")
    
    all_valid = True
    
    for workflow_file in workflow_files:
        valid, message = validate_workflow(workflow_file)
        
        if valid:
            print(f"✅ {workflow_file.name}: {message}")
        else:
            print(f"❌ {workflow_file.name}: {message}")
            all_valid = False
    
    if all_valid:
        print("\n🎉 All workflow files are valid!")
        return 0
    else:
        print("\n❌ Some workflow files have issues")
        return 1

if __name__ == '__main__':
    sys.exit(main())
