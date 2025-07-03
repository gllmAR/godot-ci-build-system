"""
Config parser for Godot Build System (project-agnostic)
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class StructureConfig:
    projects_dir: Optional[str] = None
    docs_dir: Optional[str] = None
    cache_dir: Optional[str] = None
    site_root: Optional[str] = None
    sidebar_file: Optional[str] = None
    index_file: Optional[str] = None
    exports_subdir: Optional[str] = None


@dataclass
class LoggingConfig:
    verbose_downloads: Optional[bool] = None
    progress_updates: Optional[bool] = None
    ci_mode: Optional[bool] = None


@dataclass
class DeploymentConfig:
    allow_partial_failures: Optional[bool] = None
    max_failure_rate: Optional[float] = None
    exclude_godot_binaries: Optional[bool] = None
    exclude_templates: Optional[bool] = None


@dataclass
class BuildSystemConfig:
    project_name: Optional[str] = None
    project_url: Optional[str] = None
    godot_version: Optional[str] = None
    python_version: Optional[str] = None
    max_parallel_jobs: Optional[int] = None
    enable_web_exports: Optional[bool] = None
    enable_documentation_generation: Optional[bool] = None
    enable_embed_injection: Optional[bool] = None
    enable_sidebar_generation: Optional[bool] = None
    enable_caching: Optional[bool] = None
    verbose_output: Optional[bool] = None
    dry_run_mode: Optional[bool] = None
    structure: StructureConfig = field(default_factory=StructureConfig)
    project_include_patterns: List[str] = field(default_factory=list)
    project_exclude_patterns: List[str] = field(default_factory=list)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)

    @classmethod
    def from_json_file(cls, config_path: Path) -> 'BuildSystemConfig':
        with open(config_path, 'r') as f:
            data = json.load(f)
        structure_data = data.pop('structure', {})
        logging_data = data.pop('logging', {})
        deployment_data = data.pop('deployment', {})
        structure = StructureConfig(**structure_data)
        logging = LoggingConfig(**logging_data)
        deployment = DeploymentConfig(**deployment_data)
        return cls(
            **data,
            structure=structure,
            logging=logging,
            deployment=deployment
        )

    def apply_to_environment(self, env_dict: Dict[str, Any]) -> None:
        if self.godot_version is not None:
            env_dict['GODOT_VERSION'] = self.godot_version
        if self.max_parallel_jobs is not None:
            env_dict['MAX_PARALLEL_JOBS'] = self.max_parallel_jobs
        if self.enable_caching is not None:
            env_dict['ENABLE_CACHING'] = self.enable_caching
        if self.verbose_output is not None:
            env_dict['VERBOSE_OUTPUT'] = self.verbose_output
        if self.dry_run_mode is not None:
            env_dict['DRY_RUN_MODE'] = self.dry_run_mode


def load_config(config_path: Optional[Path] = None) -> BuildSystemConfig:
    if config_path is None:
        current = Path.cwd()
        for path in [current] + list(current.parents):
            config_file = path / "build_config.json"
            if config_file.exists():
                config_path = config_file
                break
    if config_path and config_path.exists():
        return BuildSystemConfig.from_json_file(config_path)
    else:
        raise FileNotFoundError("build_config.json not found. Please run the configuration wizard.")
