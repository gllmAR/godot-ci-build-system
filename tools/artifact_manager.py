"""
Artifact Manager
================

Handles packaging, validation, and preparation of build artifacts for deployment.
This module encapsulates CI/CD artifact management logic.
"""

import os
import shutil
import zipfile
import json
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
import tempfile
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
class ArtifactInfo:
    """Information about a build artifact"""
    path: Path
    size: int
    artifact_type: str
    metadata: Optional[Dict[str, Any]] = None


class ArtifactManager:
    """Manages build artifacts for deployment"""
    
    def __init__(self, progress_reporter: Optional[ProgressReporter] = None):
        self.progress = progress_reporter or ProgressReporter()
        
    def clean_build_artifacts(self, projects_dir: Path) -> int:
        """Clean existing build artifacts from projects directory"""
        
        self.progress.info("🧹 Cleaning existing build artifacts...")
        
        artifacts_cleaned = 0
        patterns_to_clean = [
            "exports",
            "*.wasm", 
            "*.pck",
            "*.tmp",
            "*.log",
            "build_cache.json",
            ".godot"
        ]
        
        for pattern in patterns_to_clean:
            if pattern.startswith("*."):
                # File patterns
                for file_path in projects_dir.rglob(pattern):
                    try:
                        file_path.unlink()
                        artifacts_cleaned += 1
                    except Exception as e:
                        self.progress.warning(f"⚠️  Could not remove {file_path}: {e}")
            else:
                # Directory patterns
                for dir_path in projects_dir.rglob(pattern):
                    if dir_path.is_dir():
                        try:
                            shutil.rmtree(dir_path)
                            artifacts_cleaned += 1
                        except Exception as e:
                            self.progress.warning(f"⚠️  Could not remove {dir_path}: {e}")
        
        self.progress.success(f"✅ Cleaned {artifacts_cleaned} build artifacts")
        return artifacts_cleaned
    
    def verify_build_results(self, projects_dir: Path) -> Dict[str, Any]:
        """Verify and analyze build results"""
        
        self.progress.info("🔍 Verifying build results...")
        
        # Count projects
        project_files = list(projects_dir.rglob("project.godot"))
        total_projects = len(project_files)
        
        # Count exports
        export_indices = list(projects_dir.rglob("*/exports/*/index.html"))
        total_exports = len(export_indices)
        
        # Count export directories
        export_dirs = list(projects_dir.rglob("exports"))
        export_dirs = [d for d in export_dirs if d.is_dir()]
        
        # Analyze web exports specifically
        web_exports = []
        for export_index in export_indices:
            export_dir = export_index.parent
            
            # Check for required web export files
            has_wasm = any(export_dir.glob("*.wasm"))
            has_pck = any(export_dir.glob("*.pck"))
            has_js = any(export_dir.glob("*.js"))
            
            web_exports.append({
                "path": str(export_index.relative_to(projects_dir)),
                "dir": str(export_dir.relative_to(projects_dir)),
                "has_wasm": has_wasm,
                "has_pck": has_pck,
                "has_js": has_js,
                "complete": has_wasm and has_pck and has_js
            })
        
        # Count complete vs incomplete exports
        complete_exports = sum(1 for export in web_exports if export["complete"])
        
        results = {
            "total_projects": total_projects,
            "export_dirs": len(export_dirs),
            "total_exports": total_exports,
            "complete_exports": complete_exports,
            "incomplete_exports": total_exports - complete_exports,
            "success_rate": (complete_exports / total_projects * 100) if total_projects > 0 else 0,
            "web_exports": web_exports[:5],  # Sample of exports for debugging
            "export_paths": [str(p.relative_to(projects_dir)) for p in export_indices[:5]]
        }
        
        # Report results
        self.progress.info(f"📊 Build verification results:")
        self.progress.info(f"  📋 Total projects: {total_projects}")
        self.progress.info(f"  📁 Export directories: {len(export_dirs)}")
        self.progress.info(f"  🌐 Total exports: {total_exports}")
        self.progress.info(f"  ✅ Complete exports: {complete_exports}")
        self.progress.info(f"  ⚠️  Incomplete exports: {total_exports - complete_exports}")
        self.progress.info(f"  📈 Success rate: {results['success_rate']:.1f}%")
        
        if results['export_paths']:
            self.progress.info(f"  📝 Sample exports:")
            for path in results['export_paths']:
                self.progress.info(f"    - {path}")
        
        return results
    
    def prepare_documentation_artifact(self, 
                                     root_dir: Path, 
                                     projects_dir: Path,
                                     output_dir: Optional[Path] = None) -> Path:
        """Prepare documentation site artifact for deployment"""
        
        self.progress.info("📦 Preparing documentation artifact...")
        
        if output_dir is None:
            output_dir = root_dir / "artifact_staging"
        
        output_dir.mkdir(exist_ok=True)
        
        # Documentation files to include
        doc_files = [
            "index.html",
            "_sidebar.md", 
            "README.md",
            "DOCS.md",
            "docsify-embed-godot.js"
        ]
        
        # Copy documentation files
        copied_files = []
        for doc_file in doc_files:
            src_path = root_dir / doc_file
            if src_path.exists():
                dest_path = output_dir / doc_file
                shutil.copy2(src_path, dest_path)
                copied_files.append(doc_file)
                self.progress.info(f"  📄 Copied {doc_file}")
        
        # Copy projects directory with filters
        dest_projects_dir = output_dir / projects_dir.name
        if dest_projects_dir.exists():
            shutil.rmtree(dest_projects_dir)
        
        self.progress.info(f"  📁 Copying projects directory...")
        
        # Define what to exclude
        exclude_patterns = {
            ".git", ".gitignore", ".gitmodules",
            ".import", "*.tmp", "*.log", 
            "build_cache.json", ".godot",
            # Godot binaries and templates
            "godot", "godot.exe", "*.tpz", 
            "export_templates", ".local/share/godot",
            "Godot_v*", "*.dmg", "*.app"
        }
        
        def ignore_patterns(dir_path, names):
            ignored = []
            for name in names:
                # Skip hidden git files
                if name.startswith('.git'):
                    ignored.append(name)
                # Skip import and cache files
                elif name in exclude_patterns:
                    ignored.append(name)
                # Skip files matching patterns
                elif any(name.endswith(pattern[1:]) for pattern in exclude_patterns if pattern.startswith('*')):
                    ignored.append(name)
                # Skip Godot binaries (case-insensitive)
                elif name.lower().startswith('godot') and (name.lower().endswith('.exe') or '.' not in name):
                    ignored.append(name)
                # Skip export template files
                elif name.endswith('.tpz') or 'template' in name.lower():
                    ignored.append(name)
            return ignored
        
        shutil.copytree(projects_dir, dest_projects_dir, ignore=ignore_patterns)
        
        # Calculate artifact info
        total_size = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file())
        total_files = len(list(output_dir.rglob("*")))
        
        # Verify artifact contents
        verification = self.verify_build_results(dest_projects_dir)
        
        self.progress.success(f"✅ Documentation artifact prepared:")
        self.progress.info(f"  📦 Location: {output_dir}")
        self.progress.info(f"  📄 Documentation files: {len(copied_files)}")
        self.progress.info(f"  🎮 Projects: {verification['total_projects']}")
        self.progress.info(f"  🌐 Web exports: {verification['total_exports']}")
        self.progress.info(f"  📁 Total files: {total_files}")
        self.progress.info(f"  💾 Total size: {self._format_size(total_size)}")
        
        return output_dir
    
    def create_deployment_summary(self, artifact_dir: Path) -> Dict[str, Any]:
        """Create a summary of deployment artifact"""
        
        # Verify projects structure
        projects_dirs = [d for d in artifact_dir.iterdir() if d.is_dir() and d.name.endswith('-projects')]
        
        if not projects_dirs:
            projects_dir = artifact_dir / "godot-demo-projects"  # Default
        else:
            projects_dir = projects_dirs[0]
        
        summary = {
            "artifact_path": str(artifact_dir),
            "created_at": str(artifact_dir.stat().st_mtime),
            "total_size": sum(f.stat().st_size for f in artifact_dir.rglob("*") if f.is_file()),
            "total_files": len(list(artifact_dir.rglob("*"))),
        }
        
        # Add build verification if projects exist
        if projects_dir.exists():
            verification = self.verify_build_results(projects_dir)
            summary.update(verification)
        
        # Check for documentation files
        doc_files = ["index.html", "_sidebar.md", "README.md", "docsify-embed-godot.js"]
        summary["documentation_files"] = [
            doc for doc in doc_files 
            if (artifact_dir / doc).exists()
        ]
        
        return summary
    
    def validate_for_deployment(self, artifact_dir: Path, config=None) -> List[str]:
        """Validate artifact is ready for deployment"""
        
        self.progress.info("🔍 Validating artifact for deployment...")
        
        issues = []
        warnings = []
        
        # Check for required documentation files
        required_docs = ["index.html", "_sidebar.md"]
        for doc in required_docs:
            if not (artifact_dir / doc).exists():
                issues.append(f"Missing required documentation file: {doc}")
        
        # Check for projects directory
        projects_dirs = [d for d in artifact_dir.iterdir() if d.is_dir() and 'project' in d.name.lower()]
        if not projects_dirs:
            issues.append("No projects directory found in artifact")
        else:
            projects_dir = projects_dirs[0]
            
            # Count total projects and exports
            total_projects = len(list(projects_dir.rglob("project.godot")))
            export_indices = list(projects_dir.rglob("*/exports/*/index.html"))
            export_count = len(export_indices)
            
            if export_count == 0:
                issues.append("No web exports found in projects")
            else:
                # Check individual exports and collect warnings (not critical issues)
                incomplete_exports = []
                for export_index in export_indices:
                    export_dir = export_index.parent
                    project_rel_path = export_dir.relative_to(projects_dir).parent.parent
                    
                    missing_files = []
                    if not any(export_dir.glob("*.wasm")):
                        missing_files.append("WASM")
                    if not any(export_dir.glob("*.pck")):
                        missing_files.append("PCK")
                    
                    if missing_files:
                        incomplete_exports.append(f"{project_rel_path} (missing: {', '.join(missing_files)})")
                
                # Report incomplete exports as warnings if within acceptable limits
                if incomplete_exports:
                    failure_rate = (len(incomplete_exports) / total_projects) * 100
                    max_failure_rate = (config and hasattr(config, 'deployment') and 
                                      getattr(config.deployment, 'max_failure_rate', 10.0)) or 10.0
                    
                    if failure_rate <= max_failure_rate:
                        self.progress.warning(f"⚠️  {len(incomplete_exports)} incomplete exports ({failure_rate:.1f}% failure rate, within {max_failure_rate:.1f}% limit)")
                        for export in incomplete_exports[:5]:  # Show first 5
                            warnings.append(f"Incomplete export: {export}")
                        if len(incomplete_exports) > 5:
                            warnings.append(f"... and {len(incomplete_exports) - 5} more incomplete exports")
                    else:
                        self.progress.error(f"❌ Too many incomplete exports: {failure_rate:.1f}% exceeds {max_failure_rate:.1f}% limit")
                        issues.extend([f"Incomplete export: {export}" for export in incomplete_exports])
        
        # Check for Godot binaries and templates that shouldn't be included
        exclude_patterns = ["godot", "*.tpz", "export_templates", ".godot"]
        excluded_items = []
        for pattern in exclude_patterns:
            found_items = list(artifact_dir.rglob(pattern))
            if found_items:
                excluded_items.extend(found_items)
        
        if excluded_items:
            warnings.append(f"Found {len(excluded_items)} items that should be excluded (Godot binaries/templates)")
        
        # Report validation results
        if warnings:
            self.progress.warning(f"⚠️  Validation completed with {len(warnings)} warnings:")
            for warning in warnings:
                self.progress.warning(f"  - {warning}")
        
        if issues:
            self.progress.error(f"❌ Validation failed with {len(issues)} critical issues:")
            for issue in issues:
                self.progress.error(f"  - {issue}")
        else:
            self.progress.success("✅ Artifact validation passed")
        
        return issues
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        size_float = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_float < 1024.0:
                return f"{size_float:.1f}{unit}"
            size_float /= 1024.0
        return f"{size_float:.1f}TB"


def prepare_deployment_artifact(root_dir: Path, 
                               projects_dir: Path,
                               output_dir: Optional[Path] = None,
                               progress_reporter: Optional[ProgressReporter] = None) -> Path:
    """Convenience function to prepare deployment artifact"""
    
    manager = ArtifactManager(progress_reporter)
    return manager.prepare_documentation_artifact(root_dir, projects_dir, output_dir)


if __name__ == "__main__":
    # CLI for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Artifact Manager")
    parser.add_argument("--clean", help="Clean artifacts in directory", metavar="DIR")
    parser.add_argument("--verify", help="Verify build results in directory", metavar="DIR")
    parser.add_argument("--prepare", help="Prepare deployment artifact", action="store_true")
    parser.add_argument("--root-dir", help="Root directory", default=".", type=Path)
    parser.add_argument("--projects-dir", help="Projects directory", default="godot-demo-projects", type=Path)
    parser.add_argument("--output-dir", help="Output directory for artifact", type=Path)
    
    args = parser.parse_args()
    
    manager = ArtifactManager()
    
    if args.clean:
        clean_dir = Path(args.clean)
        count = manager.clean_build_artifacts(clean_dir)
        print(f"Cleaned {count} artifacts")
    
    elif args.verify:
        verify_dir = Path(args.verify)
        results = manager.verify_build_results(verify_dir)
        print(f"Verification results: {json.dumps(results, indent=2)}")
    
    elif args.prepare:
        artifact_dir = manager.prepare_documentation_artifact(
            args.root_dir, 
            args.projects_dir, 
            args.output_dir
        )
        print(f"Artifact prepared at: {artifact_dir}")
        
        # Validate the artifact
        issues = manager.validate_for_deployment(artifact_dir)
        if issues:
            print(f"Validation issues: {issues}")
            exit(1)
        else:
            print("Artifact validation passed")
    
    else:
        parser.print_help()
