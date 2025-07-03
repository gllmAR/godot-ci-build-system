"""
Modern Build Environment for Godot Examples Documentation
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any

from tools.parallel_manager import ParallelManager
from tools.environment_manager import setup_godot_environment
from tools.progress_reporter import ProgressReporter


class ModernBuildEnvironment:
    """Modern build environment replacing the legacy SCons system"""
    
    def __init__(self, **kwargs):
        self.config = {
            'godot_binary': kwargs.get('godot_binary', 'godot'),
            'projects_dir': Path(kwargs.get('projects_dir', 'godot-demo-projects')),
            'max_parallel_jobs': kwargs.get('max_parallel_jobs', None),
            'show_progress': kwargs.get('show_progress', False),
            'enable_caching': kwargs.get('enable_caching', True),
            'verbose': kwargs.get('verbose', False),
            'dry_run': kwargs.get('dry_run', False),
        }
        
        self.parallel_manager = ParallelManager()
        if self.config['max_parallel_jobs'] is None:
            self.config['max_parallel_jobs'] = self.parallel_manager.get_optimal_job_count()
    
    def setup_environment(self, godot_version: Optional[str] = None) -> bool:
        """Setup the build environment"""
        try:
            # Setup Godot environment if version is specified
            if godot_version:
                success = setup_godot_environment(
                    version=godot_version,
                    force_reinstall=False,
                    progress_reporter=None
                )
                
                if not success:
                    return False
            
            # Verify Godot is available
            result = subprocess.run(
                [self.config['godot_binary'], '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return result.returncode == 0
            
        except Exception as e:
            if self.config['verbose']:
                print(f"Environment setup failed: {e}")
            return False
    
    def get_parallel_jobs(self) -> int:
        """Get the number of parallel jobs to use"""
        return self.config['max_parallel_jobs']
    
    def is_dry_run(self) -> bool:
        """Check if this is a dry run"""
        return self.config['dry_run']
    
    def is_verbose(self) -> bool:
        """Check if verbose output is enabled"""
        return self.config['verbose']
