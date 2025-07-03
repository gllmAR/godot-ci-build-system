"""
Change Detection
================

Handles intelligent change detection for incremental builds.
This module provides smart analysis of what needs to be rebuilt.
"""

import os
import subprocess
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

try:
    from .progress_reporter import ProgressReporter
except ImportError:
    # Fallback for CLI execution
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from progress_reporter import ProgressReporter


@dataclass
class ChangeInfo:
    """Information about detected changes"""
    changed_files: List[str]
    changed_projects: Set[str]
    build_system_changed: bool
    docs_changed: bool
    force_rebuild: bool
    reason: str


class ChangeDetector:
    """Detects changes that require rebuilding"""
    
    def __init__(self, progress_reporter: Optional[ProgressReporter] = None):
        self.progress = progress_reporter or ProgressReporter()
        
    def detect_git_changes(self, 
                          repo_dir: Path, 
                          base_ref: str = "HEAD~1",
                          force_rebuild: bool = False) -> ChangeInfo:
        """Detect changes using Git"""
        
        self.progress.info("🔍 Detecting changes using Git...")
        
        if force_rebuild:
            self.progress.info("🔄 Force rebuild requested - all changes detected")
            return ChangeInfo(
                changed_files=[],
                changed_projects=set(),
                build_system_changed=True,
                docs_changed=True,
                force_rebuild=True,
                reason="Force rebuild requested"
            )
        
        # Check for CI environment - force rebuild in CI to ensure fresh builds
        # This is critical for CI/CD pipelines that use shallow clones (fetch-depth: 1)
        # where change detection may fail due to limited git history
        ci_indicators = ['CI', 'GITHUB_ACTIONS', 'GITLAB_CI', 'TRAVIS', 'CIRCLECI', 'JENKINS_URL']
        is_ci = any(os.environ.get(var) for var in ci_indicators)
        
        if is_ci:
            self.progress.info("🤖 CI environment detected - forcing full rebuild for reliable deployment")
            return ChangeInfo(
                changed_files=[],
                changed_projects=set(),
                build_system_changed=True,
                docs_changed=True,
                force_rebuild=True,
                reason="CI environment detected - ensuring fresh build"
            )
        
        try:
            # First, check if the base_ref exists
            ref_check = subprocess.run(
                ["git", "rev-parse", "--verify", base_ref],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if ref_check.returncode != 0:
                self.progress.warning(f"⚠️  Reference '{base_ref}' not found, using fallback strategy")
                # Try to use the first commit or current state
                try:
                    # Get first commit hash
                    first_commit = subprocess.run(
                        ["git", "rev-list", "--max-parents=0", "HEAD"],
                        cwd=repo_dir,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if first_commit.returncode == 0 and first_commit.stdout.strip():
                        base_ref = first_commit.stdout.strip()
                        self.progress.info(f"🔄 Using first commit as base: {base_ref[:8]}")
                    else:
                        # No commits or git history, force full rebuild
                        self.progress.info("🔄 No git history found, forcing full rebuild")
                        return ChangeInfo(
                            changed_files=[],
                            changed_projects=set(),
                            build_system_changed=True,
                            docs_changed=True,
                            force_rebuild=True,
                            reason="No git history - first build"
                        )
                except:
                    # Git operations failed, fall back to full rebuild
                    return ChangeInfo(
                        changed_files=[],
                        changed_projects=set(),
                        build_system_changed=True,
                        docs_changed=True,
                        force_rebuild=True,
                        reason="Git operations failed - assuming all changed"
                    )
            
            # Get changed files since base_ref
            result = subprocess.run(
                ["git", "diff", "--name-only", base_ref, "HEAD"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.progress.warning(f"⚠️  Git diff failed: {result.stderr}")
                # Fall back to full rebuild
                return ChangeInfo(
                    changed_files=[],
                    changed_projects=set(),
                    build_system_changed=True,
                    docs_changed=True,
                    force_rebuild=True,
                    reason="Git diff failed - assuming all changed"
                )
            
            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Special case: If we're comparing the same commit (shallow clone scenario)
            # and no changes detected, but we used a fallback strategy, force rebuild
            # This handles edge cases where CI detection might be missed but we're still
            # in a shallow clone situation that needs a full build
            if not changed_files and base_ref != "HEAD~1":
                # Check if base_ref equals HEAD (indicating shallow clone)
                head_check = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if head_check.returncode == 0 and head_check.stdout.strip() == base_ref:
                    self.progress.info("🔄 Shallow clone detected - forcing full rebuild")
                    return ChangeInfo(
                        changed_files=[],
                        changed_projects=set(),
                        build_system_changed=True,
                        docs_changed=True,
                        force_rebuild=True,
                        reason="Shallow clone detected - first build"
                    )
            
            # Analyze changes
            return self._analyze_changes(changed_files, repo_dir)
            
        except subprocess.TimeoutExpired:
            self.progress.error("❌ Git diff timeout")
            return ChangeInfo(
                changed_files=[],
                changed_projects=set(),
                build_system_changed=True,
                docs_changed=True,
                force_rebuild=True,
                reason="Git timeout - assuming all changed"
            )
        except Exception as e:
            self.progress.error(f"❌ Git detection failed: {e}")
            return ChangeInfo(
                changed_files=[],
                changed_projects=set(),
                build_system_changed=True,
                docs_changed=True,
                force_rebuild=True,
                reason=f"Git error: {e}"
            )
    
    def detect_filesystem_changes(self, 
                                 repo_dir: Path,
                                 cache_file: Optional[Path] = None) -> ChangeInfo:
        """Detect changes using filesystem timestamps and hashes"""
        
        self.progress.info("🔍 Detecting changes using filesystem...")
        
        if cache_file is None:
            cache_file = repo_dir / "build_system" / "cache" / "change_cache.json"
        
        # Load previous state
        previous_state = self._load_cache(cache_file)
        current_state = self._scan_filesystem(repo_dir)
        
        # Compare states
        changed_files = []
        for file_path, file_info in current_state.items():
            if file_path not in previous_state:
                changed_files.append(file_path)
            elif previous_state[file_path] != file_info:
                changed_files.append(file_path)
        
        # Check for deleted files
        for file_path in previous_state:
            if file_path not in current_state:
                changed_files.append(file_path)
        
        # Save current state
        self._save_cache(cache_file, current_state)
        
        # Analyze changes
        return self._analyze_changes(changed_files, repo_dir)
    
    def _analyze_changes(self, changed_files: List[str], repo_dir: Path) -> ChangeInfo:
        """Analyze which changes require rebuilding"""
        
        if not changed_files:
            self.progress.info("✅ No changes detected")
            return ChangeInfo(
                changed_files=[],
                changed_projects=set(),
                build_system_changed=False,
                docs_changed=False,
                force_rebuild=False,
                reason="No changes detected"
            )
        
        changed_projects = set()
        build_system_changed = False
        docs_changed = False
        
        # Patterns that indicate build system changes
        build_system_patterns = [
            "build_system/",
            "build.sh",
            "build_config.json",
            "requirements.txt",
            ".py$",
            "SConstruct",
            ".github/workflows/"
        ]
        
        # Patterns that indicate documentation changes
        docs_patterns = [
            "index.html",
            "_sidebar.md",
            "README.md",
            "DOCS.md",
            "docsify-embed-godot.js",
            ".md$"
        ]
        
        # Analyze each changed file
        for file_path in changed_files:
            self.progress.info(f"  📝 Changed: {file_path}")
            
            # Check if it's a build system change
            if any(pattern.replace("$", "") in file_path or 
                   (pattern.endswith("$") and file_path.endswith(pattern[:-1]))
                   for pattern in build_system_patterns):
                build_system_changed = True
            
            # Check if it's a documentation change
            if any(pattern.replace("$", "") in file_path or 
                   (pattern.endswith("$") and file_path.endswith(pattern[:-1]))
                   for pattern in docs_patterns):
                docs_changed = True
            
            # Check if it affects specific projects
            if "godot-demo-projects/" in file_path or "-projects/" in file_path:
                # Extract project name from path
                path_parts = file_path.split("/")
                for i, part in enumerate(path_parts):
                    if "projects" in part and i + 1 < len(path_parts):
                        # Next part should be category (2d, 3d, etc.)
                        if i + 2 < len(path_parts):
                            category = path_parts[i + 1]
                            project = path_parts[i + 2]
                            changed_projects.add(f"{category}/{project}")
                        break
        
        # Determine rebuild scope
        if build_system_changed:
            reason = "Build system changes detected"
            # Build system changes affect everything
            changed_projects = set()  # Will rebuild all
        elif changed_projects:
            reason = f"Project changes detected: {', '.join(list(changed_projects)[:3])}"
            if len(changed_projects) > 3:
                reason += f" and {len(changed_projects) - 3} more"
        elif docs_changed:
            reason = "Documentation changes detected"
        else:
            reason = "Other changes detected"
        
        self.progress.info(f"📊 Change analysis:")
        self.progress.info(f"  📝 Changed files: {len(changed_files)}")
        self.progress.info(f"  🎮 Affected projects: {len(changed_projects) if changed_projects else 'all' if build_system_changed else 'none'}")
        self.progress.info(f"  🔧 Build system changed: {build_system_changed}")
        self.progress.info(f"  📚 Documentation changed: {docs_changed}")
        self.progress.info(f"  🎯 Reason: {reason}")
        
        return ChangeInfo(
            changed_files=changed_files,
            changed_projects=changed_projects,
            build_system_changed=build_system_changed,
            docs_changed=docs_changed,
            force_rebuild=False,
            reason=reason
        )
    
    def _scan_filesystem(self, repo_dir: Path) -> Dict[str, str]:
        """Scan filesystem and create state snapshot"""
        
        state = {}
        
        # Patterns of files to track
        track_patterns = [
            "**/*.py",
            "**/*.sh", 
            "**/*.json",
            "**/*.yml",
            "**/*.yaml",
            "**/*.md",
            "**/*.html",
            "**/*.js",
            "**/project.godot",
            "**/export_presets.cfg",
            "**/SConstruct"
        ]
        
        for pattern in track_patterns:
            for file_path in repo_dir.glob(pattern):
                if file_path.is_file():
                    try:
                        # Use relative path as key
                        rel_path = str(file_path.relative_to(repo_dir))
                        
                        # Skip certain directories
                        if any(skip in rel_path for skip in ['.git/', '__pycache__/', '.godot/', 'cache/']):
                            continue
                        
                        # Create file signature (mtime + size + hash of first/last 1KB)
                        stat = file_path.stat()
                        signature = f"{stat.st_mtime}:{stat.st_size}"
                        
                        # For small files, hash the whole thing
                        # For large files, hash first and last 1KB
                        if stat.st_size < 2048:
                            with open(file_path, 'rb') as f:
                                signature += ":" + hashlib.md5(f.read()).hexdigest()[:8]
                        else:
                            with open(file_path, 'rb') as f:
                                first_chunk = f.read(1024)
                                f.seek(-1024, 2)  # Seek to 1KB from end
                                last_chunk = f.read(1024)
                                combined = first_chunk + last_chunk
                                signature += ":" + hashlib.md5(combined).hexdigest()[:8]
                        
                        state[rel_path] = signature
                        
                    except Exception as e:
                        self.progress.warning(f"⚠️  Could not scan {file_path}: {e}")
        
        return state
    
    def _load_cache(self, cache_file: Path) -> Dict[str, str]:
        """Load previous filesystem state from cache"""
        
        if not cache_file.exists():
            return {}
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return data.get('filesystem_state', {})
        except Exception as e:
            self.progress.warning(f"⚠️  Could not load change cache: {e}")
            return {}
    
    def _save_cache(self, cache_file: Path, state: Dict[str, str]):
        """Save current filesystem state to cache"""
        
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'filesystem_state': state
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            self.progress.warning(f"⚠️  Could not save change cache: {e}")


def detect_changes(repo_dir: Path, 
                  base_ref: str = "HEAD~1",
                  force_rebuild: bool = False,
                  use_git: bool = True,
                  progress_reporter: Optional[ProgressReporter] = None) -> ChangeInfo:
    """Convenience function to detect changes"""
    
    detector = ChangeDetector(progress_reporter)
    
    if use_git:
        return detector.detect_git_changes(repo_dir, base_ref, force_rebuild)
    else:
        return detector.detect_filesystem_changes(repo_dir)


if __name__ == "__main__":
    # CLI for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Change Detector")
    parser.add_argument("--repo-dir", help="Repository directory", default=".", type=Path)
    parser.add_argument("--base-ref", help="Base reference for git diff", default="HEAD~1")
    parser.add_argument("--force", help="Force rebuild", action="store_true")
    parser.add_argument("--no-git", help="Use filesystem instead of git", action="store_true")
    
    args = parser.parse_args()
    
    changes = detect_changes(
        args.repo_dir,
        args.base_ref, 
        args.force,
        not args.no_git
    )
    
    print(f"Change detection results:")
    print(f"  Changed files: {len(changes.changed_files)}")
    print(f"  Changed projects: {len(changes.changed_projects) if changes.changed_projects else 'all' if changes.build_system_changed else 'none'}")
    print(f"  Build system changed: {changes.build_system_changed}")
    print(f"  Documentation changed: {changes.docs_changed}")
    print(f"  Force rebuild: {changes.force_rebuild}")
    print(f"  Reason: {changes.reason}")
    
    if changes.changed_files:
        print(f"  Files:")
        for file_path in changes.changed_files[:10]:
            print(f"    - {file_path}")
        if len(changes.changed_files) > 10:
            print(f"    ... and {len(changes.changed_files) - 10} more")
