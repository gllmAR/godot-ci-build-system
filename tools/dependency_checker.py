#!/usr/bin/env python3
"""
Dependency Checker for Godot Examples Documentation Build System
================================================================

Cross-platform dependency checking and installation guidance.
Supports macOS, Linux distributions, and Windows.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class DependencyChecker:
    """Cross-platform dependency checker and installer guide"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.architecture = platform.machine()
        self.python_version = sys.version_info
        self.missing_deps = []
        self.warnings = []
        
        # Define required dependencies
        self.dependencies = {
            'python': {
                'command': ['python3', '--version'],
                'min_version': (3, 6),
                'required': True,
                'description': 'Python 3.6 or higher'
            },
            'godot': {
                'command': ['godot', '--version'],
                'required': True,
                'description': 'Godot Engine'
            },
            'git': {
                'command': ['git', '--version'],
                'required': False,
                'description': 'Git version control (recommended)'
            }
        }
        
        # Python packages
        self.python_packages = {
            'psutil': {
                'import_name': 'psutil',
                'required': True,
                'description': 'System and process monitoring'
            }
        }
    
    def check_all_dependencies(self) -> bool:
        """Check all dependencies and return True if all required ones are met"""
        print("🔍 Checking system dependencies...")
        print(f"📊 System: {self.system.title()} {self.architecture}")
        print(f"🐍 Python: {sys.version}")
        print("=" * 60)
        
        all_good = True
        
        # Check system dependencies
        for name, config in self.dependencies.items():
            if not self._check_command(name, config):
                if config['required']:
                    all_good = False
                    self.missing_deps.append(name)
                else:
                    self.warnings.append(name)
        
        # Check Python packages
        for name, config in self.python_packages.items():
            if not self._check_python_package(name, config):
                if config['required']:
                    all_good = False
                    self.missing_deps.append(f"python-{name}")
                else:
                    self.warnings.append(f"python-{name}")
        
        # Print results
        self._print_results(all_good)
        
        return all_good
    
    def _check_command(self, name: str, config: Dict) -> bool:
        """Check if a command is available"""
        try:
            result = subprocess.run(
                config['command'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                # Special version check for Python
                if name == 'python' and 'min_version' in config:
                    if self.python_version >= config['min_version']:
                        print(f"✅ {config['description']}: Found")
                        return True
                    else:
                        print(f"❌ {config['description']}: Version too old ({sys.version.split()[0]})")
                        return False
                else:
                    print(f"✅ {config['description']}: Found")
                    return True
            else:
                print(f"❌ {config['description']}: Not found")
                return False
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ {config['description']}: Not found")
            return False
    
    def _check_python_package(self, name: str, config: Dict) -> bool:
        """Check if a Python package is available"""
        try:
            __import__(config['import_name'])
            print(f"✅ Python package '{name}': Found")
            return True
        except ImportError:
            print(f"❌ Python package '{name}': Not found")
            return False
    
    def _print_results(self, all_good: bool):
        """Print dependency check results"""
        print("=" * 60)
        
        if all_good:
            print("🎉 All required dependencies are satisfied!")
            if self.warnings:
                print(f"⚠️  Optional dependencies missing: {', '.join(self.warnings)}")
        else:
            print("❌ Missing required dependencies!")
            print(f"📋 Missing: {', '.join(self.missing_deps)}")
        
        print()
    
    def show_installation_guide(self):
        """Show installation guide for missing dependencies"""
        if not self.missing_deps and not self.warnings:
            return
        
        print("📖 Installation Guide")
        print("=" * 60)
        
        all_deps = self.missing_deps + self.warnings
        
        if self.system == 'darwin':  # macOS
            self._show_macos_guide(all_deps)
        elif self.system == 'linux':
            self._show_linux_guide(all_deps)
        elif self.system == 'windows':
            self._show_windows_guide(all_deps)
        else:
            self._show_generic_guide(all_deps)
    
    def _show_macos_guide(self, deps: List[str]):
        """Show macOS installation guide"""
        print("🍎 macOS Installation Guide")
        print("-" * 30)
        
        # Check if Homebrew is available
        has_homebrew = shutil.which('brew') is not None
        
        if not has_homebrew:
            print("📦 First, install Homebrew:")
            print('   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
            print()
        
        for dep in deps:
            if dep == 'scons':
                print("🔧 Install SCons:")
                print("   brew install scons")
            elif dep == 'godot':
                print("🎮 Install Godot Engine:")
                print("   brew install godot")
                print("   # Alternative: Download from https://godotengine.org/download")
            elif dep == 'git':
                print("📝 Install Git:")
                print("   brew install git")
            elif dep.startswith('python-'):
                pkg = dep.replace('python-', '')
                print(f"🐍 Install Python package '{pkg}':")
                print(f"   pip3 install --user {pkg}")
                print(f"   # Or in virtual environment: pip install {pkg}")
            print()
    
    def _show_linux_guide(self, deps: List[str]):
        """Show Linux installation guide"""
        print("🐧 Linux Installation Guide")
        print("-" * 30)
        
        # Detect package manager
        pkg_managers = [
            ('apt', ['apt', 'apt-get']),  # Debian/Ubuntu
            ('yum', ['yum', 'dnf']),      # RedHat/Fedora
            ('pacman', ['pacman']),       # Arch
            ('zypper', ['zypper']),       # openSUSE
        ]
        
        detected_pm = None
        for pm_name, commands in pkg_managers:
            if any(shutil.which(cmd) for cmd in commands):
                detected_pm = pm_name
                break
        
        for dep in deps:
            if dep == 'scons':
                print("🔧 Install SCons:")
                if detected_pm == 'apt':
                    print("   sudo apt update && sudo apt install scons")
                elif detected_pm == 'yum':
                    print("   sudo dnf install scons  # or: sudo yum install scons")
                elif detected_pm == 'pacman':
                    print("   sudo pacman -S scons")
                elif detected_pm == 'zypper':
                    print("   sudo zypper install scons")
                else:
                    print("   # Use your distribution's package manager to install 'scons'")
                    print("   pip3 install --user scons")
                    
            elif dep == 'godot':
                print("🎮 Install Godot Engine:")
                if detected_pm == 'apt':
                    print("   # Option 1: Snap package")
                    print("   sudo snap install godot-4")
                    print("   # Option 2: Download from https://godotengine.org/download")
                elif detected_pm == 'pacman':
                    print("   sudo pacman -S godot")
                else:
                    print("   # Download from https://godotengine.org/download")
                    print("   # Or check your distribution's package repository")
                    
            elif dep == 'git':
                print("📝 Install Git:")
                if detected_pm == 'apt':
                    print("   sudo apt install git")
                elif detected_pm == 'yum':
                    print("   sudo dnf install git")
                elif detected_pm == 'pacman':
                    print("   sudo pacman -S git")
                elif detected_pm == 'zypper':
                    print("   sudo zypper install git")
                else:
                    print("   # Use your distribution's package manager to install 'git'")
                    
            elif dep.startswith('python-'):
                pkg = dep.replace('python-', '')
                print(f"🐍 Install Python package '{pkg}':")
                print(f"   pip3 install --user {pkg}")
                print(f"   # Or in virtual environment: pip install {pkg}")
            print()
    
    def _show_windows_guide(self, deps: List[str]):
        """Show Windows installation guide"""
        print("🪟 Windows Installation Guide")
        print("-" * 30)
        
        # Check if Chocolatey is available
        has_choco = shutil.which('choco') is not None
        
        if not has_choco:
            print("📦 Recommended: Install Chocolatey package manager:")
            print('   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString(\'https://community.chocolatey.org/install.ps1\'))')
            print("   (Run in PowerShell as Administrator)")
            print()
        
        for dep in deps:
            if dep == 'python':
                print("🐍 Install Python:")
                if has_choco:
                    print("   choco install python")
                print("   # Alternative: Download from https://www.python.org/downloads/")
                
            elif dep == 'scons':
                print("🔧 Install SCons:")
                print("   pip install scons")
                if has_choco:
                    print("   # Alternative: choco install scons")
                    
            elif dep == 'godot':
                print("🎮 Install Godot Engine:")
                if has_choco:
                    print("   choco install godot")
                print("   # Alternative: Download from https://godotengine.org/download")
                
            elif dep == 'git':
                print("📝 Install Git:")
                if has_choco:
                    print("   choco install git")
                print("   # Alternative: Download from https://git-scm.com/download/win")
                
            elif dep.startswith('python-'):
                pkg = dep.replace('python-', '')
                print(f"🐍 Install Python package '{pkg}':")
                print(f"   pip install {pkg}")
            print()
    
    def _show_generic_guide(self, deps: List[str]):
        """Show generic installation guide"""
        print("🌐 Generic Installation Guide")
        print("-" * 30)
        
        for dep in deps:
            if dep == 'python':
                print("🐍 Python: https://www.python.org/downloads/")
            elif dep == 'scons':
                print("🔧 SCons: pip install scons OR https://scons.org/pages/download.html")
            elif dep == 'godot':
                print("🎮 Godot Engine: https://godotengine.org/download")
            elif dep == 'git':
                print("📝 Git: https://git-scm.com/downloads")
            elif dep.startswith('python-'):
                pkg = dep.replace('python-', '')
                print(f"🐍 Python package '{pkg}': pip install {pkg}")
            print()
    
    def install_python_packages(self):
        """Attempt to install missing Python packages"""
        missing_python_deps = [dep.replace('python-', '') for dep in self.missing_deps if dep.startswith('python-')]
        
        if not missing_python_deps:
            return True
        
        print("🔧 Attempting to install missing Python packages...")
        
        # Check if we're in a virtual environment
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        pip_cmd = ['pip'] if in_venv else ['pip3', '--user']
        
        for package in missing_python_deps:
            try:
                print(f"   Installing {package}...")
                result = subprocess.run(
                    pip_cmd + ['install', package],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print(f"   ✅ Successfully installed {package}")
                else:
                    print(f"   ❌ Failed to install {package}")
                    print(f"      Error: {result.stderr.strip()}")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Error installing {package}: {e}")
                return False
        
        return True


def check_dependencies(auto_install: bool = False) -> bool:
    """
    Check all dependencies and optionally attempt auto-installation
    
    Args:
        auto_install: Whether to attempt automatic installation of Python packages
        
    Returns:
        bool: True if all required dependencies are satisfied
    """
    checker = DependencyChecker()
    
    # Check all dependencies
    all_good = checker.check_all_dependencies()
    
    # Show installation guide if needed
    if not all_good or checker.warnings:
        checker.show_installation_guide()
    
    # Attempt auto-installation of Python packages if requested
    if auto_install and not all_good:
        print("🚀 Attempting automatic installation of Python packages...")
        if checker.install_python_packages():
            print("✅ Python packages installed successfully!")
            # Re-check dependencies
            print("\n🔄 Re-checking dependencies...")
            all_good = checker.check_all_dependencies()
        else:
            print("❌ Some Python packages failed to install automatically.")
    
    return all_good


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Check build system dependencies')
    parser.add_argument('--auto-install', action='store_true', 
                        help='Attempt to automatically install missing Python packages')
    
    args = parser.parse_args()
    
    success = check_dependencies(auto_install=args.auto_install)
    sys.exit(0 if success else 1)
