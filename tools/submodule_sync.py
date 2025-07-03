#!/usr/bin/env python3
"""
Submodule Sync Tool
===================

Synchronizes Git submodules to the latest commit on their default branch.
Designed for CI environments with proper error handling and logging.
"""

import os
import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    from .progress_reporter import ProgressReporter
except ImportError:
    # Fallback for CLI execution
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from progress_reporter import ProgressReporter


class SubmoduleSync:
    """Handles synchronizing Git submodules to latest commits"""
    
    def __init__(self, repo_root: Path, progress_reporter: Optional[ProgressReporter] = None):
        self.repo_root = Path(repo_root).resolve()
        self.progress = progress_reporter or ProgressReporter()
        
    def sync_all_submodules(self, 
                           commit_changes: bool = True,
                           branch_name: str = "auto-update-submodules",
                           create_pr: bool = False) -> bool:
        """
        Sync all submodules to their latest commits
        
        Args:
            commit_changes: Whether to commit the submodule updates
            branch_name: Branch name for the update (used if create_pr is True)
            create_pr: Whether to create a pull request (requires GitHub CLI)
            
        Returns:
            True if successful, False if any errors occurred
        """
        
        self.progress.info("🔄 Starting submodule synchronization...")
        
        # Get submodule information
        submodules = self._get_submodules()
        if not submodules:
            self.progress.warning("⚠️  No submodules found in repository")
            return True
        
        self.progress.info(f"📋 Found {len(submodules)} submodule(s) to sync")
        
        success = True
        updated_submodules = []
        
        for submodule in submodules:
            self.progress.info(f"🔍 Processing submodule: {submodule['name']}")
            
            # Sync this submodule
            old_commit, new_commit = self._sync_submodule(submodule)
            
            if old_commit != new_commit:
                updated_submodules.append({
                    'name': submodule['name'],
                    'path': submodule['path'],
                    'old_commit': old_commit,
                    'new_commit': new_commit,
                    'url': submodule['url']
                })
                self.progress.success(f"✅ Updated {submodule['name']}: {old_commit[:8]} → {new_commit[:8]}")
            else:
                self.progress.info(f"✨ {submodule['name']} already up to date")
        
        if not updated_submodules:
            self.progress.success("🎉 All submodules are already up to date!")
            return True
        
        # Commit changes if requested
        if commit_changes:
            if create_pr:
                success = self._create_update_pr(updated_submodules, branch_name)
            else:
                success = self._commit_submodule_updates(updated_submodules)
        else:
            self.progress.info("📝 Submodule updates completed but not committed (commit_changes=False)")
        
        return success
    
    def _get_submodules(self) -> List[Dict[str, str]]:
        """Get list of submodules from .gitmodules"""
        
        gitmodules_path = self.repo_root / ".gitmodules"
        if not gitmodules_path.exists():
            return []
        
        try:
            # Parse .gitmodules file
            result = subprocess.run(
                ["git", "config", "--file", str(gitmodules_path), "--list"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.progress.error(f"❌ Failed to parse .gitmodules: {result.stderr}")
                return []
            
            submodules = {}
            for line in result.stdout.strip().split('\n'):
                if not line or '=' not in line:
                    continue
                
                key, value = line.split('=', 1)
                parts = key.split('.')
                if len(parts) == 3 and parts[0] == 'submodule':
                    submodule_name = parts[1]
                    property_name = parts[2]
                    
                    if submodule_name not in submodules:
                        submodules[submodule_name] = {'name': submodule_name}
                    
                    submodules[submodule_name][property_name] = value
            
            return list(submodules.values())
            
        except Exception as e:
            self.progress.error(f"❌ Error reading submodules: {e}")
            return []
    
    def _sync_submodule(self, submodule: Dict[str, str]) -> Tuple[str, str]:
        """
        Sync a single submodule to latest commit
        
        Returns:
            Tuple of (old_commit, new_commit)
        """
        
        submodule_path = self.repo_root / submodule['path']
        
        # Get current commit
        old_commit = self._get_current_commit(submodule_path)
        if not old_commit:
            self.progress.error(f"❌ Could not get current commit for {submodule['name']}")
            return "", ""
        
        try:
            # Initialize/update submodule if needed
            self._ensure_submodule_initialized(submodule)
            
            # Fetch latest changes
            self.progress.info(f"📡 Fetching latest changes for {submodule['name']}...")
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=submodule_path,
                check=True,
                capture_output=True,
                timeout=120
            )
            
            # Determine default branch
            default_branch = self._get_default_branch(submodule_path)
            if not default_branch:
                self.progress.warning(f"⚠️  Could not determine default branch for {submodule['name']}, using 'main'")
                default_branch = "main"
            
            # Update to latest commit on default branch
            self.progress.info(f"🔄 Updating {submodule['name']} to latest {default_branch}...")
            subprocess.run(
                ["git", "checkout", f"origin/{default_branch}"],
                cwd=submodule_path,
                check=True,
                capture_output=True,
                timeout=30
            )
            
            # Get new commit
            new_commit = self._get_current_commit(submodule_path)
            if not new_commit:
                self.progress.error(f"❌ Could not get new commit for {submodule['name']}")
                return old_commit, old_commit
            
            return old_commit, new_commit
            
        except subprocess.CalledProcessError as e:
            self.progress.error(f"❌ Git command failed for {submodule['name']}: {e}")
            return old_commit, old_commit
        except Exception as e:
            self.progress.error(f"❌ Error syncing {submodule['name']}: {e}")
            return old_commit, old_commit
    
    def _ensure_submodule_initialized(self, submodule: Dict[str, str]):
        """Ensure submodule is properly initialized"""
        
        submodule_path = self.repo_root / submodule['path']
        
        if not submodule_path.exists() or not (submodule_path / ".git").exists():
            self.progress.info(f"🔧 Initializing submodule {submodule['name']}...")
            subprocess.run(
                ["git", "submodule", "update", "--init", submodule['path']],
                cwd=self.repo_root,
                check=True,
                timeout=120
            )
    
    def _get_current_commit(self, path: Path) -> str:
        """Get current commit hash for a repository"""
        
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            
        except Exception:
            pass
        
        return ""
    
    def _get_default_branch(self, path: Path) -> str:
        """Get the default branch name for a repository"""
        
        try:
            # Try to get default branch from remote
            result = subprocess.run(
                ["git", "remote", "show", "origin"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'HEAD branch:' in line:
                        return line.split('HEAD branch:')[-1].strip()
            
            # Fallback: check common branch names
            for branch in ['main', 'master']:
                result = subprocess.run(
                    ["git", "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch}"],
                    cwd=path,
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    return branch
            
        except Exception:
            pass
        
        return "main"  # Default fallback
    
    def _commit_submodule_updates(self, updated_submodules: List[Dict]) -> bool:
        """Commit submodule updates to the parent repository"""
        
        try:
            # Stage submodule changes
            for submodule in updated_submodules:
                subprocess.run(
                    ["git", "add", submodule['path']],
                    cwd=self.repo_root,
                    check=True
                )
            
            # Create commit message
            commit_msg = self._generate_commit_message(updated_submodules)
            
            # Commit changes
            self.progress.info("💾 Committing submodule updates...")
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.repo_root,
                check=True
            )
            
            self.progress.success("✅ Submodule updates committed successfully!")
            return True
            
        except subprocess.CalledProcessError as e:
            self.progress.error(f"❌ Failed to commit submodule updates: {e}")
            return False
    
    def _create_update_pr(self, updated_submodules: List[Dict], branch_name: str) -> bool:
        """Create a pull request for submodule updates"""
        
        try:
            # Create new branch
            self.progress.info(f"🌿 Creating branch: {branch_name}")
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.repo_root,
                check=True
            )
            
            # Commit changes
            if not self._commit_submodule_updates(updated_submodules):
                return False
            
            # Push branch
            self.progress.info(f"📤 Pushing branch: {branch_name}")
            subprocess.run(
                ["git", "push", "origin", branch_name],
                cwd=self.repo_root,
                check=True
            )
            
            # Create PR using GitHub CLI (if available)
            pr_title = f"🤖 Auto-update submodules ({datetime.now().strftime('%Y-%m-%d')})"
            pr_body = self._generate_pr_body(updated_submodules)
            
            self.progress.info("🔄 Creating pull request...")
            subprocess.run(
                ["gh", "pr", "create", "--title", pr_title, "--body", pr_body],
                cwd=self.repo_root,
                check=True
            )
            
            self.progress.success("✅ Pull request created successfully!")
            return True
            
        except subprocess.CalledProcessError as e:
            self.progress.error(f"❌ Failed to create pull request: {e}")
            self.progress.info("💡 Make sure GitHub CLI (gh) is installed and authenticated")
            return False
    
    def _generate_commit_message(self, updated_submodules: List[Dict]) -> str:
        """Generate a commit message for submodule updates"""
        
        if len(updated_submodules) == 1:
            sub = updated_submodules[0]
            return f"🤖 Update {sub['name']} submodule ({sub['old_commit'][:8]} → {sub['new_commit'][:8]})"
        else:
            lines = ["🤖 Update submodules to latest versions", ""]
            for sub in updated_submodules:
                lines.append(f"- {sub['name']}: {sub['old_commit'][:8]} → {sub['new_commit'][:8]}")
            return "\n".join(lines)
    
    def _generate_pr_body(self, updated_submodules: List[Dict]) -> str:
        """Generate a pull request body for submodule updates"""
        
        lines = [
            "## 🤖 Automated Submodule Update",
            "",
            "This PR updates the following submodules to their latest versions:",
            ""
        ]
        
        for sub in updated_submodules:
            lines.extend([
                f"### {sub['name']}",
                f"- **Repository**: {sub['url']}",
                f"- **Old commit**: [`{sub['old_commit'][:8]}`]({sub['url']}/commit/{sub['old_commit']})",
                f"- **New commit**: [`{sub['new_commit'][:8]}`]({sub['url']}/commit/{sub['new_commit']})",
                f"- **Compare**: [{sub['old_commit'][:8]}...{sub['new_commit'][:8]}]({sub['url']}/compare/{sub['old_commit']}...{sub['new_commit']})",
                ""
            ])
        
        lines.extend([
            "---",
            "",
            "🔍 **Review Notes:**",
            "- This is an automated update to keep submodules in sync",
            "- Please review the changes in the linked repositories",
            "- Test the build to ensure compatibility",
            "",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        ])
        
        return "\n".join(lines)


def sync_submodules(repo_root: Optional[Path] = None,
                   commit_changes: bool = True,
                   create_pr: bool = False,
                   branch_name: Optional[str] = None,
                   progress_reporter: Optional[ProgressReporter] = None) -> bool:
    """
    Convenience function to sync submodules
    
    Args:
        repo_root: Root directory of the repository (defaults to current working directory)
        commit_changes: Whether to commit the updates
        create_pr: Whether to create a pull request
        branch_name: Branch name for PR (auto-generated if None)
        progress_reporter: Progress reporter instance
        
    Returns:
        True if successful, False otherwise
    """
    
    if repo_root is None:
        repo_root = Path.cwd()
    
    if branch_name is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"auto-update-submodules-{timestamp}"
    
    syncer = SubmoduleSync(repo_root, progress_reporter)
    return syncer.sync_all_submodules(commit_changes, branch_name, create_pr)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Synchronize Git submodules to latest versions")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(),
                       help="Root directory of the repository")
    parser.add_argument("--no-commit", action="store_true",
                       help="Don't commit the submodule updates")
    parser.add_argument("--create-pr", action="store_true",
                       help="Create a pull request for the updates")
    parser.add_argument("--branch-name", type=str,
                       help="Branch name for pull request")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Create progress reporter
    progress = ProgressReporter(verbose=args.verbose)
    
    # Run synchronization
    success = sync_submodules(
        repo_root=args.repo_root,
        commit_changes=not args.no_commit,
        create_pr=args.create_pr,
        branch_name=args.branch_name,
        progress_reporter=progress
    )
    
    sys.exit(0 if success else 1)
