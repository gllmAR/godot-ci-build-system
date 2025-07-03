#!/usr/bin/env python3
"""
Godot Project Exporter for Web/HTML5 Builds
===========================================

Handles real Godot project exports to HTML5/Web format using the Godot command line.
Replaces placeholder HTML exports with actual compiled Godot games.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import json

try:
    from .progress_reporter import ProgressReporter
except ImportError:
    # Fallback for CLI execution
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from progress_reporter import ProgressReporter


@dataclass
class ExportResult:
    """Result of a Godot export operation"""
    success: bool
    project_path: Path
    export_path: Path
    error_message: Optional[str] = None
    export_size: Optional[int] = None
    export_time: Optional[float] = None


class GodotExporter:
    """Handles Godot project exports to web format"""
    
    def __init__(self, godot_binary: str = "godot", progress_reporter: Optional[ProgressReporter] = None):
        self.godot_binary = godot_binary
        self.progress = progress_reporter or ProgressReporter()
        self.web_export_preset = "Web"
        
    def verify_godot_binary(self) -> bool:
        """Verify that Godot binary is available and working"""
        try:
            result = subprocess.run(
                [self.godot_binary, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def create_web_export_preset(self, project_path: Path) -> bool:
        """Create or update web export preset for a project"""
        export_presets_path = project_path / "export_presets.cfg"
        
        # Basic web export preset configuration
        web_preset_config = """[preset.0]

name="Web"
platform="Web"
runnable=true
advanced_options=false
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="exports/web/index.html"
encryption_include_filters=""
encryption_exclude_filters=""
encrypt_pck=false
encrypt_directory=false

[preset.0.options]

custom_template/debug=""
custom_template/release=""
variant/extensions_support=false
vram_texture_compression/for_desktop=true
vram_texture_compression/for_mobile=false
html/export_icon=true
html/custom_html_shell=""
html/head_include=""
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
html/experimental_virtual_keyboard=false
progressive_web_app/enabled=false
progressive_web_app/offline_page=""
progressive_web_app/display=1
progressive_web_app/orientation=0
progressive_web_app/icon_144x144=""
progressive_web_app/icon_180x180=""
progressive_web_app/icon_512x512=""
progressive_web_app/background_color=Color(0, 0, 0, 1)
"""
        
        try:
            # Write export presets
            export_presets_path.write_text(web_preset_config)
            return True
        except Exception as e:
            self.progress.error(f"Failed to create export preset: {e}")
            return False
    
    def export_project_to_web(self, project_path: Path, force_rebuild: bool = False) -> ExportResult:
        """Export a single Godot project to web format"""
        project_file = project_path / "project.godot"
        if not project_file.exists():
            return ExportResult(
                success=False,
                project_path=project_path,
                export_path=Path(),
                error_message="No project.godot file found"
            )
        
        # Setup export directory
        export_dir = project_path / "exports" / "web"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        export_file = export_dir / "index.html"
        
        # Check if export already exists and is newer than project files
        if export_file.exists() and not force_rebuild:
            if self._is_export_up_to_date(project_path, export_file):
                return ExportResult(
                    success=True,
                    project_path=project_path,
                    export_path=export_file,
                    export_size=self._get_export_size(export_dir)
                )
        
        # Create export preset if needed
        if not self.create_web_export_preset(project_path):
            return ExportResult(
                success=False,
                project_path=project_path,
                export_path=export_file,
                error_message="Failed to create export preset"
            )
        
        # Run Godot export
        start_time = time.time()
        export_cmd = [
            self.godot_binary,
            "--headless",
            "--path", str(project_path.absolute()),
            "--export-release", self.web_export_preset, str(export_file.absolute())
        ]
        
        try:
            self.progress.info(f"🎮 Exporting {project_path.name} to web...")
            
            # Add environment variables for better stability
            env = os.environ.copy()
            env.update({
                'GODOT_DISABLE_CRASH_HANDLER': '1',  # Disable crash handler for better error reporting
                'DISPLAY': ':0' if 'DISPLAY' not in env else env['DISPLAY'],  # Ensure display is set
            })
            
            result = subprocess.run(
                export_cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=project_path,
                env=env
            )
            
            export_time = time.time() - start_time
            
            if result.returncode == 0 and export_file.exists():
                export_size = self._get_export_size(export_dir)
                self.progress.success(f"✅ Exported {project_path.name} ({export_size} bytes, {export_time:.1f}s)")
                
                return ExportResult(
                    success=True,
                    project_path=project_path,
                    export_path=export_file,
                    export_size=export_size,
                    export_time=export_time
                )
            else:
                # Enhanced error analysis
                error_details = self._analyze_export_error(result.returncode, result.stderr, result.stdout)
                error_msg = f"Export failed (code {result.returncode}): {error_details}"
                self.progress.error(f"❌ Failed to export {project_path.name}: {error_msg}")
                
                return ExportResult(
                    success=False,
                    project_path=project_path,
                    export_path=export_file,
                    error_message=error_msg
                )
                
        except subprocess.TimeoutExpired:
            error_msg = "Export timed out after 5 minutes"
            self.progress.error(f"❌ {project_path.name}: {error_msg}")
            
            return ExportResult(
                success=False,
                project_path=project_path,
                export_path=export_file,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"Export error: {e}"
            self.progress.error(f"❌ {project_path.name}: {error_msg}")
            
            return ExportResult(
                success=False,
                project_path=project_path,
                export_path=export_file,
                error_message=error_msg
            )
    
    def export_project_with_retry(self, project_path: Path, max_retries: int = 3, force_rebuild: bool = False) -> ExportResult:
        """Export a project with retry logic for handling system errors"""
        last_error = None
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                self.progress.info(f"🔄 Retry {attempt}/{max_retries} for {project_path.name}")
                # Wait progressively longer before retry to let system recover
                import time
                wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                time.sleep(wait_time)
                
                # Try to free up some resources
                try:
                    import gc
                    gc.collect()
                except:
                    pass
            
            result = self.export_project_to_web(project_path, force_rebuild)
            
            if result.success:
                return result
            
            last_error = result.error_message
            
            # Check if this is a retryable error
            if result.error_message and any(err in result.error_message.lower() for err in [
                'invalid argument', 'system_error', 'std::system_error', 
                'resource temporarily unavailable', 'cannot allocate memory',
                'too many open files', 'out of memory'
            ]):
                if attempt < max_retries:
                    self.progress.warning(f"⚠️ Retryable system error for {project_path.name} (attempt {attempt + 1}), retrying...")
                    continue
            else:
                # Non-retryable error, fail immediately
                break
        
        # All retries failed, return the last error
        self.progress.error(f"❌ All retry attempts failed for {project_path.name}")
        return ExportResult(
            success=False,
            project_path=project_path,
            export_path=Path(),
            error_message=f"Failed after {max_retries + 1} attempts: {last_error}"
        )
    
    def export_projects_parallel(self, project_files: List[Path], max_workers: int = 4, force_rebuild: bool = False) -> List[ExportResult]:
        """Export multiple projects in parallel"""
        import time
        import concurrent.futures
        
        results = []
        
        # Group projects to avoid overwhelming the system
        batch_size = min(max_workers, len(project_files))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
            # Submit all export tasks with retry capability
            future_to_project = {
                executor.submit(self.export_project_with_retry, project_file.parent, 3, force_rebuild): project_file
                for project_file in project_files
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_project):
                project_file = future_to_project[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update progress
                    completed = len(results)
                    total = len(project_files)
                    self.progress.update_progress(
                        f"Exported {completed}/{total} projects",
                        (completed / total) * 100
                    )
                    
                except Exception as e:
                    self.progress.error(f"❌ Exception exporting {project_file.parent.name}: {e}")
                    results.append(ExportResult(
                        success=False,
                        project_path=project_file.parent,
                        export_path=Path(),
                        error_message=f"Exception: {e}"
                    ))
        
        return results
    
    def _is_export_up_to_date(self, project_path: Path, export_file: Path) -> bool:
        """Check if export is newer than project source files"""
        if not export_file.exists():
            return False
        
        export_time = export_file.stat().st_mtime
        
        # Check common project files
        for pattern in ["*.gd", "*.cs", "*.tscn", "*.tres", "project.godot"]:
            for file_path in project_path.rglob(pattern):
                if file_path.stat().st_mtime > export_time:
                    return False
        
        return True
    
    def _get_export_size(self, export_dir: Path) -> int:
        """Get total size of exported files"""
        total_size = 0
        for file_path in export_dir.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def get_export_summary(self, results: List[ExportResult]) -> Dict[str, Any]:
        """Generate summary statistics for export results"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        total_size = sum(r.export_size or 0 for r in successful)
        total_time = sum(r.export_time or 0 for r in successful)
        avg_time = total_time / len(successful) if successful else 0
        
        return {
            "total_projects": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) if results else 0,
            "total_export_size": total_size,
            "total_export_time": total_time,
            "average_export_time": avg_time,
            "failed_projects": [r.project_path.name for r in failed]
        }
    
    def _analyze_export_error(self, returncode: int, stderr: str, stdout: str) -> str:
        """Analyze Godot export error and provide helpful diagnostics"""
        # Common error patterns and solutions
        error_patterns = {
            -6: "System resource error - try reducing parallel jobs or check memory/file descriptors",
            -9: "Process killed - likely out of memory or timeout",
            -11: "Segmentation fault - corrupted project or missing dependencies",
            1: "Export template or preset issue",
            2: "Project file or path issue",
            127: "Godot binary not found or not executable"
        }
        
        # Get base error description
        base_error = error_patterns.get(returncode, f"Unknown error code {returncode}")
        
        # Analyze stderr for specific issues
        if stderr:
            stderr_lower = stderr.lower()
            if "invalid argument" in stderr_lower and "std::system_error" in stderr_lower:
                base_error += " - Likely file descriptor/resource limit reached. Try: ulimit -n 4096"
            elif "invalid argument" in stderr_lower:
                base_error += " - Check file paths, permissions, or reduce concurrent exports"
            elif "cannot allocate memory" in stderr_lower or "out of memory" in stderr_lower:
                base_error += " - Insufficient memory, reduce parallel jobs with --jobs N"
            elif "too many open files" in stderr_lower:
                base_error += " - File descriptor limit exceeded, try: ulimit -n 4096"
            elif "template" in stderr_lower and "not found" in stderr_lower:
                base_error += " - Export templates missing, run: godot --export-debug Web"
            elif "permission denied" in stderr_lower:
                base_error += " - Permission error, check file/directory permissions"
            elif "display" in stderr_lower or "x11" in stderr_lower:
                base_error += " - Display/X11 issue in headless environment, set DISPLAY=:0"
        
        # Include relevant stderr excerpt
        if stderr and len(stderr.strip()) > 0:
            stderr_excerpt = stderr.strip()[:300] + ("..." if len(stderr) > 300 else "")
            return f"{base_error}\nDetails: {stderr_excerpt}"
        
        return base_error


def create_fallback_export(project_path: Path, export_dir: Path) -> bool:
    """Create a fallback HTML export for projects that can't be exported"""
    export_file = export_dir / "index.html"
    
    fallback_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{project_path.name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #2d3748;
            color: #e2e8f0;
        }}
        .container {{
            text-align: center;
            padding: 40px;
            background: #4a5568;
            border-radius: 8px;
        }}
        .icon {{ font-size: 48px; margin-bottom: 20px; }}
        h1 {{ color: #63b3ed; margin-bottom: 20px; }}
        .info {{ margin: 20px 0; }}
        .note {{ 
            background: #2d3748; 
            padding: 15px; 
            border-radius: 5px;
            border-left: 4px solid #63b3ed;
            margin: 20px 0;
        }}
        a {{ color: #63b3ed; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">🎮</div>
        <h1>Godot Project: {project_path.name}</h1>
        <div class="info">
            <p>This project requires the full Godot engine to run.</p>
            <p>Project location: <code>{project_path.name}</code></p>
        </div>
        <div class="note">
            <strong>Note:</strong> This is a fallback display. To see the actual game,
            clone the repository and run the project in Godot engine.
        </div>
        <p><a href="https://godotengine.org" target="_blank">Download Godot Engine</a></p>
    </div>
</body>
</html>"""
    
    try:
        export_file.write_text(fallback_html)
        return True
    except Exception:
        return False


# Import time at module level for timing functions
import time


def main():
    """CLI entry point for testing the exporter"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Export Godot projects to web format")
    parser.add_argument("project_path", help="Path to Godot project directory")
    parser.add_argument("export_path", help="Path where exported web files should be saved")
    parser.add_argument("--godot-binary", default="godot", help="Path to Godot binary")
    parser.add_argument("--dry-run", action="store_true", help="Only simulate the export")
    
    args = parser.parse_args()
    
    exporter = GodotExporter(godot_binary=args.godot_binary)
    
    if args.dry_run:
        print(f"[DRY RUN] Would export {args.project_path} to {args.export_path}")
        return
    
    # Verify Godot binary
    if not exporter.verify_godot_binary():
        print(f"Error: Godot binary '{args.godot_binary}' not found or not working")
        return 1
    
    project_path = Path(args.project_path)
    export_path = Path(args.export_path)
    
    print(f"Exporting {project_path} to {export_path}")
    result = exporter.export_project_to_web(project_path)
    
    if result.success:
        print(f"✅ Export successful!")
        if result.export_size:
            print(f"   Export size: {result.export_size} bytes")
        if result.export_time:
            print(f"   Export time: {result.export_time:.2f}s")
    else:
        print(f"❌ Export failed: {result.error_message}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())