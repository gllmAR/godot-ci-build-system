"""
Environment Manager
==================

Handles Godot engine and export template installation, validation, and setup.
This module encapsulates all the logic for setting up a complete Godot build environment.
"""

import os
import sys
import platform
import tempfile
import zipfile
import urllib.request
import urllib.error
import time
import socket
from pathlib import Path
from typing import Optional, Tuple, Dict, List
import subprocess
import shutil

try:
    from .progress_reporter import ProgressReporter
except ImportError:
    # Fallback for CLI execution
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from progress_reporter import ProgressReporter


class GodotEnvironmentManager:
    """Manages Godot engine installation and export templates"""
    
    def __init__(self, progress_reporter: Optional[ProgressReporter] = None, config=None):
        self.progress = progress_reporter or ProgressReporter()
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.config = config
        
        # Set logging preferences first (before platform info logging)
        self.verbose_downloads = (config and 
                                hasattr(config, 'logging') and 
                                getattr(config.logging, 'verbose_downloads', True))
        self.show_progress = (config and 
                            hasattr(config, 'logging') and 
                            getattr(config.logging, 'progress_updates', True))
        self.ci_mode = ((config and 
                        hasattr(config, 'logging') and 
                        getattr(config.logging, 'ci_mode', False)) or 
                       os.getenv('CI', '').lower() == 'true')
        
        # Log detected platform information
        self._log_platform_info()
    
    def _log_platform_info(self):
        """Log detected platform information for debugging"""
        platform_name = {
            'linux': 'Linux',
            'darwin': 'macOS', 
            'windows': 'Windows'
        }.get(self.system, self.system.title())
        
        # Detect more detailed architecture info
        arch_info = self._get_detailed_arch_info()
        
        if self.verbose_downloads:
            self.progress.info(f"🔍 Platform: {platform_name} ({arch_info})")
            self.progress.info(f"📦 Binary suffix: {self._get_binary_suffix()}")
    
    def _get_detailed_arch_info(self) -> str:
        """Get detailed architecture information"""
        machine = platform.machine().lower()
        processor = platform.processor().lower()
        
        # Enhanced architecture detection
        if machine in ['x86_64', 'amd64']:
            return "x86_64 (64-bit Intel/AMD)"
        elif machine in ['i386', 'i686', 'x86']:
            return "x86_32 (32-bit Intel/AMD)"
        elif machine in ['arm64', 'aarch64']:
            if 'apple' in processor or self.system == 'darwin':
                return "ARM64 (Apple Silicon)"
            else:
                return "ARM64 (64-bit ARM)"
        elif machine in ['armv7l', 'armv7']:
            return "ARM32 (32-bit ARM)"
        else:
            return f"{machine} (architecture may not be fully supported)"
    
    def get_platform_info(self) -> Dict[str, str]:
        """Get comprehensive platform information"""
        return {
            'system': self.system,
            'machine': platform.machine(),
            'processor': platform.processor(),
            'architecture': platform.architecture()[0],
            'platform': platform.platform(),
            'binary_suffix': self._get_binary_suffix(),
            'detailed_arch': self._get_detailed_arch_info()
        }
    
    def get_godot_urls(self, version: str) -> Tuple[str, str]:
        """Get download URLs for Godot binary and export templates"""
        
        # Determine if this is a pre-release version
        is_prerelease = any(tag in version.lower() for tag in ['beta', 'alpha', 'rc'])
        
        if is_prerelease:
            # Pre-release versions
            base_url = f"https://github.com/godotengine/godot-builds/releases/download/{version}"
            binary_name = f"Godot_v{version}_{self._get_binary_suffix()}"
            templates_name = f"Godot_v{version}_export_templates.tpz"
        else:
            # Stable versions
            base_url = f"https://github.com/godotengine/godot-builds/releases/download/{version}-stable"
            binary_name = f"Godot_v{version}-stable_{self._get_binary_suffix()}"
            templates_name = f"Godot_v{version}-stable_export_templates.tpz"
            
        return f"{base_url}/{binary_name}", f"{base_url}/{templates_name}"
    
    def _get_binary_suffix(self) -> str:
        """Get the appropriate binary suffix for the current platform with enhanced architecture support"""
        machine = platform.machine().lower()
        
        if self.system == "linux":
            # Enhanced Linux architecture support
            if machine in ['x86_64', 'amd64']:
                return "linux.x86_64.zip"
            elif machine in ['i386', 'i686', 'x86']:
                return "linux.x86_32.zip"
            elif machine in ['arm64', 'aarch64']:
                # ARM64 Linux support (available in newer Godot versions)
                return "linux.arm64.zip"
            elif machine in ['armv7l', 'armv7']:
                # ARM32 Linux support (less common)
                return "linux.arm32.zip"
            else:
                # Default to x86_64 for unknown architectures
                self.progress.warning(f"⚠️ Unknown Linux architecture '{machine}', defaulting to x86_64")
                return "linux.x86_64.zip"
                
        elif self.system == "darwin":  # macOS
            # macOS universal binaries work on both Intel and Apple Silicon
            return "macos.universal.zip"
            
        elif self.system == "windows":
            # Enhanced Windows architecture support
            if machine in ['amd64', 'x86_64']:
                return "win64.exe.zip"
            elif machine in ['i386', 'i686', 'x86']:
                return "win32.exe.zip"
            else:
                # Default to 64-bit for unknown architectures
                self.progress.warning(f"⚠️ Unknown Windows architecture '{machine}', defaulting to 64-bit")
                return "win64.exe.zip"
                
        else:
            raise ValueError(f"Unsupported platform: {self.system}. Supported platforms: Linux, macOS, Windows")
    
    def _get_template_version_format(self, version: str) -> str:
        """Convert version string to template directory format"""
        if "beta" in version:
            return version.replace("-beta", ".beta")
        elif "alpha" in version:
            return version.replace("-alpha", ".alpha")
        elif "rc" in version:
            return version.replace("-rc", ".rc")
        else:
            return version
    
    def download_file(self, url: str, destination: Path, description: str = "file", retries: int = 3) -> bool:
        """Download a file with progress reporting and retry logic"""
        for attempt in range(retries):
            try:
                if attempt > 0:
                    self.progress.info(f"📥 Retrying download {description} (attempt {attempt + 1}/{retries})...")
                else:
                    self.progress.info(f"📥 Downloading {description}...")
                
                if attempt == 0 and self.verbose_downloads:  # Only show URL on first attempt and if verbose
                    self.progress.info(f"🔗 URL: {url}")
                
                # Set timeout for the request
                request = urllib.request.Request(url)
                # Set socket timeout to prevent hanging
                socket.setdefaulttimeout(60)
                
                with urllib.request.urlopen(request, timeout=60) as response:
                    total_size = int(response.headers.get('content-length', 0))
                    
                    with open(destination, 'wb') as f:
                        downloaded = 0
                        last_progress = -1
                        last_update_time = time.time()
                        
                        while True:
                            start_time = time.time()
                            chunk = response.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            current_time = time.time()
                            
                            if total_size > 0 and self.show_progress:
                                progress = (downloaded / total_size) * 100
                                # In CI mode, update less frequently to reduce log spam
                                update_threshold = 5.0 if self.ci_mode else 1.0
                                update_interval = 10.0 if self.ci_mode else 2.0
                                
                                if (abs(progress - last_progress) >= update_threshold or 
                                    current_time - last_update_time >= update_interval):
                                    self.progress.update_progress(f"Downloading {description}", progress)
                                    last_progress = progress
                                    last_update_time = current_time
                            
                            # Detect if download is stalled (no data for 30 seconds)
                            if current_time - start_time > 30:
                                raise TimeoutError("Download stalled - no data received for 30 seconds")
                
                # Clear the progress line and show completion
                if self.show_progress:
                    print()  # New line to clear progress bar
                self.progress.success(f"✅ Downloaded {description}")
                return True
                
            except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
                if self.show_progress:
                    print()  # New line to clear progress bar
                if attempt < retries - 1:
                    self.progress.warning(f"⚠️  Download attempt {attempt + 1} failed: {e}")
                    if not self.ci_mode:
                        self.progress.info("🔄 Waiting 5 seconds before retry...")
                        time.sleep(5)
                    else:
                        time.sleep(2)  # Shorter wait in CI
                else:
                    self.progress.error(f"❌ Failed to download {description} after {retries} attempts: {e}")
                    return False
            except Exception as e:
                if self.show_progress:
                    print()  # New line to clear progress bar
                self.progress.error(f"❌ Unexpected error downloading {description}: {e}")
                return False
        
        return False
    
    def install_godot_binary(self, version: str, install_path: Optional[Path] = None) -> Optional[Path]:
        """Download and install Godot binary"""
        
        binary_url, _ = self.get_godot_urls(version)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / "godot.zip"
            
            # Download binary
            if not self.download_file(binary_url, zip_path, f"Godot {version}"):
                return None
            
            # Extract binary
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_file:
                    zip_file.extractall(temp_path)
                
                # Find the extracted binary
                extracted_files = list(temp_path.glob("Godot_v*"))
                if not extracted_files:
                    self.progress.error("❌ No Godot binary found in archive")
                    return None
                
                binary_file = extracted_files[0]
                
                # Determine install location
                if install_path is None:
                    if self.system == "windows":
                        install_path = Path("C:/Program Files/Godot/godot.exe")
                    else:
                        install_path = Path("/usr/local/bin/godot")
                
                # Create install directory if needed
                install_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy binary to install location
                shutil.copy2(binary_file, install_path)
                
                # Make executable on Unix systems
                if self.system != "windows":
                    os.chmod(install_path, 0o755)
                
                self.progress.success(f"✅ Godot {version} installed to {install_path}")
                return install_path
                
            except Exception as e:
                self.progress.error(f"❌ Failed to extract Godot binary: {e}")
                return None
    
    def install_export_templates(self, version: str) -> bool:
        """Download and install export templates"""
        
        _, templates_url = self.get_godot_urls(version)
        template_version = self._get_template_version_format(version)
        
        # Get templates directory
        if self.system == "windows":
            templates_base = Path(os.environ.get("APPDATA", "")) / "Godot" / "export_templates"
        else:
            templates_base = Path.home() / ".local" / "share" / "godot" / "export_templates"
        
        templates_dir = templates_base / template_version
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tpz_path = temp_path / "export_templates.tpz"
            
            # Download templates
            if not self.download_file(templates_url, tpz_path, f"export templates {version}"):
                return False
            
            # Extract templates
            try:
                self.progress.info("📦 Extracting export templates...")
                
                with zipfile.ZipFile(tpz_path, 'r') as zip_file:
                    extract_path = temp_path / "templates"
                    zip_file.extractall(extract_path)
                
                # Find templates source directory
                templates_source = extract_path / "templates" if (extract_path / "templates").exists() else extract_path
                
                # Copy templates to install directory
                for item in templates_source.iterdir():
                    if item.is_file():
                        dest = templates_dir / item.name
                        shutil.copy2(item, dest)
                        self.progress.info(f"📦 Copied {item.name}")
                
                # Create version.txt
                version_file = templates_dir / "version.txt"
                version_file.write_text(template_version)
                
                self.progress.success(f"✅ Export templates installed to {templates_dir}")
                return True
                
            except Exception as e:
                self.progress.error(f"❌ Failed to extract export templates: {e}")
                return False
    
    def verify_installation(self, version: str, godot_path: Optional[Path] = None) -> Dict[str, bool]:
        """Verify Godot installation and export templates"""
        
        results = {
            "godot_binary": False,
            "export_templates": False,
            "web_templates": False
        }
        
        # Check Godot binary
        if godot_path is None:
            godot_which = shutil.which("godot")
            if godot_which:
                godot_path = Path(godot_which)
        
        if godot_path and godot_path.exists():
            try:
                result = subprocess.run(
                    [str(godot_path), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    results["godot_binary"] = True
                    self.progress.success(f"✅ Godot binary verified: {result.stdout.strip()}")
                else:
                    self.progress.error(f"❌ Godot binary check failed: {result.stderr}")
            except Exception as e:
                self.progress.error(f"❌ Failed to verify Godot binary: {e}")
        else:
            self.progress.error("❌ Godot binary not found")
        
        # Check export templates
        template_version = self._get_template_version_format(version)
        if self.system == "windows":
            templates_dir = Path(os.environ.get("APPDATA", "")) / "Godot" / "export_templates" / template_version
        else:
            templates_dir = Path.home() / ".local" / "share" / "godot" / "export_templates" / template_version
        
        if templates_dir.exists():
            results["export_templates"] = True
            self.progress.success(f"✅ Export templates directory found: {templates_dir}")
            
            # Check for web templates specifically
            web_templates = [
                "web_debug.zip",
                "web_release.zip", 
                "web_nothreads_debug.zip",
                "web_nothreads_release.zip"
            ]
            
            found_web_templates = []
            for template in web_templates:
                template_path = templates_dir / template
                if template_path.exists():
                    found_web_templates.append(template)
            
            if found_web_templates:
                results["web_templates"] = True
                self.progress.success(f"✅ Web templates found: {', '.join(found_web_templates)}")
            else:
                self.progress.warning("⚠️  No web export templates found")
                # List what templates are available
                available = [f.name for f in templates_dir.iterdir() if f.is_file()]
                self.progress.info(f"Available templates: {', '.join(available)}")
        else:
            self.progress.error(f"❌ Export templates directory not found: {templates_dir}")
        
        return results
    
    def setup_environment(self, version: str, force_reinstall: bool = False) -> bool:
        """Complete environment setup for Godot development"""
        
        self.progress.info(f"🎮 Setting up Godot {version} environment...")
        
        # Check if already installed and working
        if not force_reinstall:
            verification = self.verify_installation(version)
            if all(verification.values()):
                self.progress.success("✅ Godot environment already set up and verified")
                return True
        
        # Install Godot binary
        self.progress.info("📥 Installing Godot binary...")
        godot_path = self.install_godot_binary(version)
        if not godot_path:
            return False
        
        # Install export templates
        self.progress.info("📥 Installing export templates...")
        if not self.install_export_templates(version):
            return False
        
        # Verify installation
        self.progress.info("🔍 Verifying installation...")
        verification = self.verify_installation(version, godot_path)
        
        if all(verification.values()):
            self.progress.success("✅ Godot environment setup completed successfully")
            return True
        else:
            self.progress.error("❌ Environment setup incomplete")
            for component, status in verification.items():
                if not status:
                    self.progress.error(f"  ❌ {component.replace('_', ' ').title()}")
            return False


def setup_godot_environment(version: str, force_reinstall: bool = False, 
                           progress_reporter: Optional[ProgressReporter] = None) -> bool:
    """Convenience function to set up Godot environment"""
    
    manager = GodotEnvironmentManager(progress_reporter)
    return manager.setup_environment(version, force_reinstall)


if __name__ == "__main__":
    # CLI for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Godot Environment Manager")
    parser.add_argument("version", help="Godot version to install")
    parser.add_argument("--force", action="store_true", help="Force reinstall")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing installation")
    
    args = parser.parse_args()
    
    manager = GodotEnvironmentManager()
    
    if args.verify_only:
        verification = manager.verify_installation(args.version)
        print(f"Verification results: {verification}")
        sys.exit(0 if all(verification.values()) else 1)
    else:
        success = manager.setup_environment(args.version, args.force)
        sys.exit(0 if success else 1)
