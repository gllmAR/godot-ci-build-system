#!/usr/bin/env python3
"""
Interactive wizard to generate build_config.json for a Godot project using the universal build system.
Outputs to the parent directory of the submodule (main project root).
"""
import json
from pathlib import Path
import sys
import re

def prompt(msg, default=None):
    try:
        if default is not None:
            msg = f"{msg} [{default}]"
        val = input(msg + ": ")
        if val is None:
            return str(default) if default is not None else ""
        val = val.strip()
        return val if val else (str(default) if default is not None else "")
    except (KeyboardInterrupt, EOFError):
        print("\n❌ Wizard cancelled by user.")
        sys.exit(1)

def guess_github_url(project_root):
    # Try to guess GitHub URL from folder structure
    parent = project_root.parent
    repo = project_root.name
    user = parent.name
    return f"https://github.com/{user}/{repo}"

def extract_homepage_url_from_readme(readme_path):
    # Look for a real homepage link (not a badge/image)
    url_regex = re.compile(r'https?://[\w./\-]+')
    with open(readme_path) as f:
        for line in f:
            # Skip badge/image lines
            if any(x in line.lower() for x in ["badge", "img", "shields.io"]):
                continue
            match = url_regex.search(line)
            if match:
                return match.group(0)
    return None

def yn(val, default):
    # Always returns bool, never errors
    s = str(val or default or "n").strip().lower()
    return s.startswith('y')

def main():
    try:
        print("\n🛠️  Godot Build System Configuration Wizard\n")
        # Detect project root and infer sane defaults
        submodule_dir = Path(__file__).parent.resolve()
        project_root = submodule_dir.parent
        project_name = project_root.name.replace('-', ' ').replace('_', ' ').title()
        # Prefer GitHub repo URL as default
        default_url = guess_github_url(project_root)
        readme_path = project_root / "README.md"
        if readme_path.exists():
            homepage_url = extract_homepage_url_from_readme(readme_path)
            if homepage_url:
                default_url = homepage_url
        # Structure defaults
        default_projects_dir = "godot-demo-projects" if (project_root / "godot-demo-projects").exists() else "projects"
        default_docs_dir = "docs" if (project_root / "docs").exists() else "documentation"
        default_cache_dir = ".build_cache"
        default_site_root = "."
        default_sidebar_file = "_sidebar.md" if (project_root / "_sidebar.md").exists() else "sidebar.md"
        default_index_file = "index.html" if (project_root / "index.html").exists() else "index.htm"
        default_exports_subdir = "exports/web"

        config = {}
        config['project_name'] = prompt("Project name", project_name)
        config['project_url'] = prompt("Project URL", default_url)
        config['godot_version'] = prompt("Godot version", "4.5-beta1")
        config['python_version'] = prompt("Python version", "3.11")
        jobs_val = prompt("Max parallel jobs (0=auto)", "0")
        try:
            jobs_int = int(jobs_val)
            config['max_parallel_jobs'] = jobs_int if jobs_int > 0 else None
        except Exception:
            config['max_parallel_jobs'] = None
        config['enable_web_exports'] = yn(prompt("Enable web exports? (y/n)", "y"), "y")
        config['enable_documentation_generation'] = yn(prompt("Enable documentation generation? (y/n)", "y"), "y")
        config['enable_embed_injection'] = yn(prompt("Enable embed injection? (y/n)", "y"), "y")
        config['enable_sidebar_generation'] = yn(prompt("Enable sidebar generation? (y/n)", "y"), "y")
        config['enable_caching'] = yn(prompt("Enable caching? (y/n)", "y"), "y")
        config['verbose_output'] = yn(prompt("Verbose output? (y/n)", "n"), "n")
        config['dry_run_mode'] = yn(prompt("Dry run mode? (y/n)", "n"), "n")

        # Structure
        print("\nProject structure settings:")
        config['structure'] = {
            'projects_dir': prompt("Projects directory", default_projects_dir),
            'docs_dir': prompt("Docs directory", default_docs_dir),
            'cache_dir': prompt("Cache directory", default_cache_dir),
            'site_root': prompt("Site root", default_site_root),
            'sidebar_file': prompt("Sidebar file", default_sidebar_file),
            'index_file': prompt("Index file", default_index_file),
            'exports_subdir': prompt("Exports subdir", default_exports_subdir),
        }
        # Logging
        config['logging'] = {
            'verbose_downloads': yn(prompt("Verbose downloads? (y/n)", "n"), "n"),
            'progress_updates': yn(prompt("Progress updates? (y/n)", "y"), "y"),
            'ci_mode': yn(prompt("CI mode? (y/n)", "n"), "n"),
        }
        # Deployment
        config['deployment'] = {
            'allow_partial_failures': yn(prompt("Allow partial failures? (y/n)", "y"), "y"),
            'max_failure_rate': float(prompt("Max failure rate (%)", "10.0") or 10.0),
            'exclude_godot_binaries': yn(prompt("Exclude Godot binaries? (y/n)", "y"), "y"),
            'exclude_templates': yn(prompt("Exclude templates? (y/n)", "y"), "y"),
        }
        # Patterns
        config['project_include_patterns'] = ["**/project.godot"]
        config['project_exclude_patterns'] = ["**/.*", "**/addons/godot-git-plugin/**", "**/exports/**"]

        out_path = project_root / "build_config.json"
        with open(out_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"\n✅ Configuration written to {out_path}\n")
    except (KeyboardInterrupt, EOFError):
        print("\n❌ Wizard cancelled by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()
