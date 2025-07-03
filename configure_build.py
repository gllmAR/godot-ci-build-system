#!/usr/bin/env python3
"""
Interactive wizard to generate build_config.json for a Godot project using the universal build system.
Outputs to the parent directory of the submodule (main project root).
"""
import json
from pathlib import Path
import sys

def prompt(msg, default=None):
    if default is not None:
        msg = f"{msg} [{default}]"
    val = input(msg + ": ").strip()
    return val or default

def main():
    print("\n🛠️  Godot Build System Configuration Wizard\n")
    config = {}
    config['project_name'] = prompt("Project name", "Godot Examples Documentation")
    config['project_url'] = prompt("Project URL", "https://example.com/")
    config['godot_version'] = prompt("Godot version", "4.5-beta1")
    config['python_version'] = prompt("Python version", "3.11")
    config['max_parallel_jobs'] = int(prompt("Max parallel jobs (0=auto)", "0")) or None
    config['enable_web_exports'] = prompt("Enable web exports? (y/n)", "y").lower().startswith('y')
    config['enable_documentation_generation'] = prompt("Enable documentation generation? (y/n)", "y").lower().startswith('y')
    config['enable_embed_injection'] = prompt("Enable embed injection? (y/n)", "y").lower().startswith('y')
    config['enable_sidebar_generation'] = prompt("Enable sidebar generation? (y/n)", "y").lower().startswith('y')
    config['enable_caching'] = prompt("Enable caching? (y/n)", "y").lower().startswith('y')
    config['verbose_output'] = prompt("Verbose output? (y/n)", "n").lower().startswith('y')
    config['dry_run_mode'] = prompt("Dry run mode? (y/n)", "n").lower().startswith('y')

    # Structure
    print("\nProject structure settings:")
    config['structure'] = {
        'projects_dir': prompt("Projects directory", "godot-demo-projects"),
        'docs_dir': prompt("Docs directory", "docs"),
        'cache_dir': prompt("Cache directory", ".build_cache"),
        'site_root': prompt("Site root", "."),
        'sidebar_file': prompt("Sidebar file", "_sidebar.md"),
        'index_file': prompt("Index file", "index.html"),
        'exports_subdir': prompt("Exports subdir", "exports/web"),
    }
    # Logging
    config['logging'] = {
        'verbose_downloads': prompt("Verbose downloads? (y/n)", "n").lower().startswith('y'),
        'progress_updates': prompt("Progress updates? (y/n)", "y").lower().startswith('y'),
        'ci_mode': prompt("CI mode? (y/n)", "n").lower().startswith('y'),
    }
    # Deployment
    config['deployment'] = {
        'allow_partial_failures': prompt("Allow partial failures? (y/n)", "y").lower().startswith('y'),
        'max_failure_rate': float(prompt("Max failure rate (%)", "10.0")),
        'exclude_godot_binaries': prompt("Exclude Godot binaries? (y/n)", "y").lower().startswith('y'),
        'exclude_templates': prompt("Exclude templates? (y/n)", "y").lower().startswith('y'),
    }
    # Patterns
    config['project_include_patterns'] = ["**/project.godot"]
    config['project_exclude_patterns'] = ["**/.*", "**/addons/godot-git-plugin/**", "**/exports/**"]

    # Always output to parent of this script's directory (main project root)
    submodule_dir = Path(__file__).parent.resolve()
    project_root = submodule_dir.parent
    out_path = project_root / "build_config.json"
    with open(out_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"\n✅ Configuration written to {out_path}\n")

if __name__ == "__main__":
    main()
