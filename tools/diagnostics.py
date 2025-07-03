"""
Build System Diagnostics
========================

Integrated diagnostics for the Godot build system.
"""

import os
import sys
import subprocess
import resource
import psutil
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from .progress_reporter import ProgressReporter
except ImportError:
    # Fallback for CLI execution
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from progress_reporter import ProgressReporter


class BuildSystemDiagnostics:
    """Comprehensive diagnostics for the Godot build system"""
    
    def __init__(self, progress_reporter: Optional[ProgressReporter] = None):
        self.progress = progress_reporter or ProgressReporter()
        self.checks_passed = 0
        self.total_checks = 0
        
    def run_all_checks(self, project_root: Path) -> bool:
        """Run all diagnostic checks and return overall health status"""
        self.progress.info("🏗️ Godot Build System Diagnostics")
        self.progress.info("=" * 40)
        
        checks = [
            self.check_godot_binary,
            self.check_system_resources,
            lambda: self.check_git_repository(project_root),
            lambda: self.check_project_structure(project_root),
            self.recommend_job_count,
            lambda: self.test_single_export(project_root)
        ]
        
        for check in checks:
            self.total_checks += 1
            try:
                result = check()
                if result:
                    self.checks_passed += 1
            except Exception as e:
                self.progress.error(f"❌ Check failed: {e}")
        
        self.progress.info("\n" + "=" * 40)
        self.progress.info(f"📊 Summary: {self.checks_passed}/{self.total_checks} checks passed")
        
        if self.checks_passed == self.total_checks:
            self.progress.success("✅ System appears ready for building!")
            return True
        else:
            self.progress.warning("⚠️  Some issues detected. Review the output above.")
            return False

    def check_godot_binary(self) -> bool:
        """Check if Godot binary is available and working"""
        self.progress.info("🔍 Checking Godot binary...")
        
        try:
            result = subprocess.run(
                ["godot", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.progress.success(f"✅ Godot found: {result.stdout.strip()}")
                return True
            else:
                self.progress.error(f"❌ Godot error: {result.stderr}")
                return False
        except FileNotFoundError:
            self.progress.error("❌ Godot binary not found in PATH")
            self.progress.info("   💡 Install Godot: https://godotengine.org/download")
            return False
        except Exception as e:
            self.progress.error(f"❌ Godot check failed: {e}")
            return False

    def check_system_resources(self) -> bool:
        """Check system resources and limits"""
        self.progress.info("\n💻 Checking system resources...")
        
        try:
            # CPU and Memory
            cpu_count = os.cpu_count()
            memory = psutil.virtual_memory()
            
            self.progress.info(f"   CPU cores: {cpu_count}")
            self.progress.info(f"   Total memory: {memory.total / (1024**3):.1f}GB")
            self.progress.info(f"   Available memory: {memory.available / (1024**3):.1f}GB")
            self.progress.info(f"   Memory usage: {memory.percent}%")
            
            # File descriptor limits
            try:
                soft_fd, hard_fd = resource.getrlimit(resource.RLIMIT_NOFILE)
                self.progress.info(f"   File descriptor limit: {soft_fd} (soft) / {hard_fd} (hard)")
                
                if soft_fd < 1024:
                    self.progress.warning("   ⚠️  Low file descriptor limit, consider: ulimit -n 4096")
            except:
                self.progress.warning("   ❌ Could not check file descriptor limits")
            
            # Process limits
            try:
                soft_proc, hard_proc = resource.getrlimit(resource.RLIMIT_NPROC)
                self.progress.info(f"   Process limit: {soft_proc} (soft) / {hard_proc} (hard)")
            except:
                self.progress.warning("   ❌ Could not check process limits")
            
            # Memory warnings
            if memory.available / (1024**3) < 2.0:
                self.progress.warning("   ⚠️  Low available memory, consider reducing parallel jobs")
            
            return True
            
        except Exception as e:
            self.progress.error(f"❌ Resource check failed: {e}")
            return False

    def check_git_repository(self, project_root: Path) -> bool:
        """Check git repository status"""
        self.progress.info("\n📂 Checking git repository...")
        
        try:
            # Check if we're in a git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=project_root
            )
            
            if result.returncode != 0:
                self.progress.warning("⚠️  Not in a git repository")
                self.progress.info("   💡 Git is optional but recommended for change detection")
                return True  # Not a failure, just informational
            
            self.progress.success("✅ Git repository detected")
            
            # Check HEAD~1 reference
            result = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD~1"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=project_root
            )
            
            if result.returncode == 0:
                self.progress.success("✅ HEAD~1 reference available")
            else:
                self.progress.info("ℹ️  HEAD~1 not available (single commit repo or first build)")
                self.progress.info("   💡 Change detection will use fallback strategy")
            
            return True
            
        except Exception as e:
            self.progress.warning(f"⚠️  Git check failed: {e}")
            return True  # Git issues are not critical failures

    def check_project_structure(self, project_root: Path) -> bool:
        """Check project structure"""
        self.progress.info("\n📁 Checking project structure...")
        
        godot_projects = project_root / "godot-demo-projects"
        if godot_projects.exists():
            project_count = len(list(godot_projects.rglob("project.godot")))
            self.progress.success(f"✅ Found {project_count} Godot projects")
            
            if project_count > 100:
                self.progress.info("   ℹ️  Large build - diagnostics will recommend conservative job counts")
            elif project_count == 0:
                self.progress.warning("   ⚠️  No project.godot files found")
                return False
            
            return True
        else:
            self.progress.error("❌ godot-demo-projects directory not found")
            self.progress.info("   💡 Expected structure: godot-demo-projects/*/project.godot")
            return False

    def recommend_job_count(self) -> bool:
        """Recommend optimal job count"""
        self.progress.info("\n⚡ Job count recommendations...")
        
        try:
            # Import ParallelManager
            sys.path.append(os.path.dirname(__file__))
            from parallel_manager import ParallelManager
            
            pm = ParallelManager()
            optimal = pm.get_optimal_job_count()
            memory_efficient = pm.get_memory_efficient_job_count(121)  # Assume 121 projects
            
            self.progress.info(f"   Optimal jobs (general): {optimal}")
            self.progress.info(f"   Memory efficient (large builds): {memory_efficient}")
            self.progress.success(f"✅ Recommendation: Use --jobs {memory_efficient}")
            
            if memory_efficient < optimal:
                self.progress.info("   ℹ️  Conservative setting due to large project count or resource limits")
            
            # Additional recommendations
            cpu_count = pm.cpu_count
            memory_gb = pm.available_memory
            
            if cpu_count >= 8 and memory_gb >= 8:
                self.progress.info("   💡 High-end system: Consider --jobs 0 for maximum speed")
            elif memory_gb < 4:
                self.progress.info("   💡 Low memory: Consider --jobs 2 for stability")
                
            return True
            
        except Exception as e:
            self.progress.error(f"❌ Could not calculate recommendations: {e}")
            return False

    def test_single_export(self, project_root: Path) -> bool:
        """Test exporting a single project"""
        self.progress.info("\n🎮 Testing single project export...")
        
        pong_path = project_root / "godot-demo-projects" / "2d" / "pong"
        if not pong_path.exists():
            self.progress.warning("⚠️  Pong project not found for testing")
            self.progress.info("   💡 Skipping export test - not critical")
            return True  # Not a critical failure
        
        try:
            sys.path.append(os.path.dirname(__file__))
            from godot_exporter import GodotExporter
            
            exporter = GodotExporter(progress_reporter=self.progress)
            result = exporter.export_project_with_retry(pong_path, max_retries=1)
            
            if result.success:
                self.progress.success("✅ Single export test successful")
                self.progress.info(f"   Export size: {result.export_size} bytes")
                if result.export_time:
                    self.progress.info(f"   Export time: {result.export_time:.1f}s")
                return True
            else:
                self.progress.warning(f"⚠️  Single export test failed: {result.error_message}")
                self.progress.info("   💡 Check Godot installation and export templates")
                return False
                
        except Exception as e:
            self.progress.warning(f"⚠️  Export test failed: {e}")
            self.progress.info("   💡 This may indicate missing dependencies or configuration issues")
            return False

    def generate_report(self, project_root: Path) -> Dict[str, Any]:
        """Generate a detailed diagnostic report"""
        try:
            sys.path.append(os.path.dirname(__file__))
            from parallel_manager import ParallelManager
            
            pm = ParallelManager()
            
            report = {
                'system': {
                    'cpu_cores': pm.cpu_count,
                    'memory_gb': round(pm.available_memory, 1),
                    'resource_limits': pm.resource_limits
                },
                'godot': {
                    'binary_available': self.check_godot_binary_availability(),
                    'version': self.get_godot_version()
                },
                'projects': {
                    'count': self.count_godot_projects(project_root),
                    'structure_valid': (project_root / "godot-demo-projects").exists()
                },
                'recommendations': {
                    'optimal_jobs': pm.get_optimal_job_count(),
                    'memory_efficient_jobs': pm.get_memory_efficient_job_count(121),
                    'max_jobs_command': '--jobs 0' if pm.cpu_count >= 4 else f'--jobs {pm.cpu_count}'
                }
            }
            
            return report
            
        except Exception as e:
            return {'error': str(e)}

    def check_godot_binary_availability(self) -> bool:
        """Quick check if Godot binary is available"""
        try:
            subprocess.run(["godot", "--version"], capture_output=True, timeout=5)
            return True
        except:
            return False

    def get_godot_version(self) -> Optional[str]:
        """Get Godot version string"""
        try:
            result = subprocess.run(
                ["godot", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None

    def count_godot_projects(self, project_root: Path) -> int:
        """Count Godot projects in the repository"""
        try:
            godot_projects = project_root / "godot-demo-projects"
            if godot_projects.exists():
                return len(list(godot_projects.rglob("project.godot")))
            return 0
        except:
            return 0


def run_diagnostics(project_root: Path, progress_reporter: Optional[ProgressReporter] = None) -> bool:
    """Convenience function to run all diagnostics"""
    diagnostics = BuildSystemDiagnostics(progress_reporter)
    return diagnostics.run_all_checks(project_root)
