"""
Dependency Scanner for Smart Build Management
"""

import os
import hashlib
from pathlib import Path


class DependencyScanner:
    """Smart dependency tracking for incremental builds"""
    
    def __init__(self):
        self.cache_file = 'cache/dependencies.cache'
        self.dependencies = {}
        self.load_cache()
    
    def load_cache(self):
        """Load dependency cache from disk"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    # Simple cache format: file_path:hash
                    for line in f:
                        if ':' in line:
                            path, hash_val = line.strip().split(':', 1)
                            self.dependencies[path] = hash_val
        except Exception as e:
            print(f"⚠️  Could not load dependency cache: {e}")
    
    def save_cache(self):
        """Save dependency cache to disk"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w') as f:
                for path, hash_val in self.dependencies.items():
                    f.write(f"{path}:{hash_val}\n")
        except Exception as e:
            print(f"⚠️  Could not save dependency cache: {e}")
    
    def get_file_hash(self, file_path):
        """Get hash of file contents with size optimization"""
        try:
            # Use file stat for quick size check first
            stat = os.stat(file_path)
            
            # For large files (>10MB), use modification time as approximation
            if stat.st_size > 10 * 1024 * 1024:
                return f"large_{stat.st_mtime}_{stat.st_size}"
            
            # For normal files, use content hash
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return None
    
    def has_changed(self, file_path):
        """Check if file has changed since last build with fast path"""
        # Quick stat check first
        try:
            current_stat = os.stat(file_path)
        except:
            return True
        
        cached_hash = self.dependencies.get(file_path)
        if cached_hash is None:
            # First time seeing this file
            current_hash = self.get_file_hash(file_path)
            self.dependencies[file_path] = current_hash
            return True
        
        # For large files, quick mtime check
        if cached_hash.startswith("large_"):
            expected_mtime = float(cached_hash.split('_')[1])
            if abs(current_stat.st_mtime - expected_mtime) < 1.0:  # 1 second tolerance
                return False
        
        # Full hash check for smaller files
        current_hash = self.get_file_hash(file_path)
        changed = cached_hash != current_hash
        
        if changed:
            self.dependencies[file_path] = current_hash
        
        return changed
    
    def scan_project_dependencies(self, project_dir):
        """Scan all dependencies for a Godot project with optimization"""
        dependencies = []
        
        # Common Godot file extensions (prioritized by frequency)
        high_priority_extensions = ['.gd', '.tscn', '.tres']
        medium_priority_extensions = ['.cs', '.png', '.jpg']
        low_priority_extensions = ['.ogg', '.wav', '.mp3', '.webp', '.svg']
        
        # Use Path for better performance
        project_path = Path(project_dir)
        
        # Fast scan using pathlib.rglob (more efficient than os.walk)
        for pattern in ['*.gd', '*.tscn', '*.tres', 'project.godot']:
            for file_path in project_path.rglob(pattern):
                # Skip exports directory
                if 'exports' not in file_path.parts:
                    dependencies.append(str(file_path))
        
        # Add other extensions only if needed
        for pattern in ['*.cs', '*.png', '*.jpg', '*.ogg', '*.wav', '*.mp3']:
            for file_path in project_path.rglob(pattern):
                if 'exports' not in file_path.parts and str(file_path) not in dependencies:
                    dependencies.append(str(file_path))
        
        return dependencies
    
    def project_needs_rebuild(self, project_dir):
        """Check if project needs to be rebuilt with early exit optimization"""
        # Quick check: if project.godot changed, rebuild
        project_file = os.path.join(project_dir, 'project.godot')
        if self.has_changed(project_file):
            return True, project_file
        
        # Check critical files first (scripts and scenes)
        critical_patterns = ['*.gd', '*.tscn', '*.tres']
        project_path = Path(project_dir)
        
        for pattern in critical_patterns:
            for file_path in project_path.rglob(pattern):
                if 'exports' not in file_path.parts:
                    if self.has_changed(str(file_path)):
                        return True, str(file_path)
        
        # Check assets if no critical changes found
        asset_patterns = ['*.cs', '*.png', '*.jpg', '*.ogg', '*.wav', '*.mp3']
        for pattern in asset_patterns:
            for file_path in project_path.rglob(pattern):
                if 'exports' not in file_path.parts:
                    if self.has_changed(str(file_path)):
                        return True, str(file_path)
        
        return False, None
