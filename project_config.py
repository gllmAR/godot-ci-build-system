"""
Modern Project Configuration for Godot Examples Documentation
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class StructureConfig:
    """Configuration for project structure"""
    projects_dir: str = "godot-demo-projects"
    docs_dir: str = "docs"
    cache_dir: str = ".build_cache"
    site_root: str = "."
    sidebar_file: str = "_sidebar.md"
    index_file: str = "index.html"
    exports_subdir: str = "exports/web"


@dataclass
class LoggingConfig:
    """Configuration for logging behavior"""
    verbose_downloads: bool = False
    progress_updates: bool = True
    ci_mode: bool = False


@dataclass
class DeploymentConfig:
    """Configuration for deployment and artifact management"""
    allow_partial_failures: bool = True
    max_failure_rate: float = 10.0
    exclude_godot_binaries: bool = True
    exclude_templates: bool = True


@dataclass
class BuildSystemConfig:
    """Main build system configuration"""
    project_name: str = "Godot Examples Documentation"
    project_url: str = "https://gllmar.github.io/godot-examples-docsh/"
    godot_version: str = "4.5-beta1"
    python_version: str = "3.11"
    max_parallel_jobs: Optional[int] = None
    enable_web_exports: bool = True
    enable_documentation_generation: bool = True
    enable_embed_injection: bool = True
    enable_sidebar_generation: bool = True
    enable_caching: bool = True
    verbose_output: bool = False
    dry_run_mode: bool = False
    structure: StructureConfig = field(default_factory=StructureConfig)
    project_include_patterns: List[str] = field(default_factory=lambda: ["**/project.godot"])
    project_exclude_patterns: List[str] = field(default_factory=lambda: [
        "**/.*",
        "**/addons/godot-git-plugin/**",
        "**/exports/**"
    ])
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)
    
    @classmethod
    def from_json_file(cls, config_path: Path) -> 'BuildSystemConfig':
        """Load configuration from JSON file"""
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        # Extract nested structures
        structure_data = data.pop('structure', {})
        logging_data = data.pop('logging', {})
        deployment_data = data.pop('deployment', {})
        
        # Create nested objects
        structure = StructureConfig(**structure_data)
        logging = LoggingConfig(**logging_data)
        deployment = DeploymentConfig(**deployment_data)
        
        # Create main config
        return cls(
            **data,
            structure=structure,
            logging=logging,
            deployment=deployment
        )
    
    def apply_to_environment(self, env_dict: Dict[str, Any]) -> None:
        """Apply configuration to environment dictionary"""
        env_dict.update({
            'GODOT_VERSION': self.godot_version,
            'MAX_PARALLEL_JOBS': self.max_parallel_jobs,
            'ENABLE_CACHING': self.enable_caching,
            'VERBOSE_OUTPUT': self.verbose_output,
            'DRY_RUN_MODE': self.dry_run_mode,
        })


def setup_build_system(project_root: Path, config_file: str = "build_config.json") -> BuildSystemConfig:
    """Setup build system with configuration"""
    config_path = project_root / config_file
    
    if config_path.exists():
        return BuildSystemConfig.from_json_file(config_path)
    else:
        # Return default configuration
        return BuildSystemConfig()


def load_config(config_path: Optional[Path] = None) -> BuildSystemConfig:
    """Load build system configuration"""
    if config_path is None:
        # Look for config in current directory and parent directories
        current = Path.cwd()
        for path in [current] + list(current.parents):
            config_file = path / "build_config.json"
            if config_file.exists():
                config_path = config_file
                break
    
    if config_path and config_path.exists():
        return BuildSystemConfig.from_json_file(config_path)
    else:
        return BuildSystemConfig()
