#!/usr/bin/env python3
"""
Embed Injector for Godot Examples Documentation
Injects embed markers into README files for Docsify integration
"""

import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from project_config import BuildSystemConfig
from tools.progress_reporter import ProgressReporter


class EmbedInjector:
    """Handles injection of embed markers into documentation files"""
    
    def __init__(self, progress_reporter: Optional[ProgressReporter] = None):
        self.progress = progress_reporter or ProgressReporter()
        self.embed_marker = "<!-- embed-{$PATH} -->"
        self.old_embed_start = "<!-- GAME_EMBED -->"
        self.old_embed_end = "<!-- /GAME_EMBED -->"
        
        self.stats = {
            'files_processed': 0,
            'embeds_added': 0,
            'old_embeds_removed': 0,
            'files_skipped': 0
        }
    
    def clean_old_embed_blocks(self, content: str) -> tuple[str, bool]:
        """
        Remove old GAME_EMBED blocks from content
        
        Args:
            content: README file content
            
        Returns:
            Tuple of (cleaned_content, was_cleaned)
        """
        was_cleaned = False
        
        if self.old_embed_start in content:
            start_pos = content.find(self.old_embed_start)
            if start_pos != -1:
                end_pos = content.find(self.old_embed_end, start_pos)
                if end_pos != -1:
                    # Remove the entire block including end marker
                    content = content[:start_pos] + content[end_pos + len(self.old_embed_end):]
                    content = content.strip() + "\n"
                    was_cleaned = True
                    self.stats['old_embeds_removed'] += 1
        
        return content, was_cleaned
    
    def inject_embed_marker(self, content: str) -> tuple[str, bool]:
        """
        Inject embed marker after H1 title if not already present
        
        Args:
            content: README file content
            
        Returns:
            Tuple of (updated_content, was_injected)
        """
        # Check if embed marker already exists
        if self.embed_marker in content:
            return content, False
        
        lines = content.split('\n')
        insert_pos = 0
        
        # Find the first H1 title
        for i, line in enumerate(lines):
            if line.strip().startswith('# '):
                insert_pos = i + 1
                break
        
        # Insert embed marker after title (with empty lines for spacing)
        if insert_pos > 0:
            lines.insert(insert_pos, "")
            lines.insert(insert_pos + 1, self.embed_marker)
            lines.insert(insert_pos + 2, "")
        else:
            # If no H1 found, add at the beginning
            lines.insert(0, self.embed_marker)
            lines.insert(1, "")
        
        self.stats['embeds_added'] += 1
        return '\n'.join(lines), True
    
    def process_readme_file(self, readme_file: Path) -> bool:
        """
        Process a single README file to inject embed markers
        
        Args:
            readme_file: Path to README.md file
            
        Returns:
            True if file was modified, False otherwise
        """
        if not readme_file.exists():
            return False
        
        try:
            content = readme_file.read_text(encoding='utf-8')
            original_content = content
            
            # Clean old embed blocks
            content, was_cleaned = self.clean_old_embed_blocks(content)
            
            # Inject new embed marker
            content, was_injected = self.inject_embed_marker(content)
            
            # Write back if content changed
            if content != original_content:
                readme_file.write_text(content, encoding='utf-8')
                self.stats['files_processed'] += 1
                return True
            else:
                self.stats['files_skipped'] += 1
                return False
                
        except Exception as e:
            self.progress.warning(f"Failed to process {readme_file}: {e}")
            return False
    
    def inject_embeds_into_projects(self, projects_dir: Path, dry_run: bool = False) -> dict:
        """
        Inject embed markers into all Godot project README files
        
        Args:
            projects_dir: Directory containing Godot projects
            dry_run: If True, don't actually modify files
            
        Returns:
            Dictionary with injection statistics
        """
        # Reset stats
        self.stats = {
            'files_processed': 0,
            'embeds_added': 0,
            'old_embeds_removed': 0,
            'files_skipped': 0
        }
        
        # Find all Godot projects
        project_files = list(projects_dir.rglob("project.godot"))
        
        if not project_files:
            self.progress.warning(f"No Godot projects found in {projects_dir}")
            return self.stats
        
        self.progress.info(f"🔍 Found {len(project_files)} projects to process")
        
        for project_file in project_files:
            project_dir = project_file.parent
            readme_file = project_dir / "README.md"
            
            if readme_file.exists():
                if dry_run:
                    self.progress.info(f"Would process: {readme_file.relative_to(projects_dir)}")
                else:
                    self.process_readme_file(readme_file)
            else:
                self.progress.warning(f"No README.md found: {project_dir.relative_to(projects_dir)}")
        
        return self.stats
    
    def generate_report(self) -> str:
        """Generate a summary report of the embed injection process"""
        report = []
        report.append("=== Embed Injection Report ===")
        report.append(f"Files processed: {self.stats['files_processed']}")
        report.append(f"Embeds added: {self.stats['embeds_added']}")
        report.append(f"Old embeds removed: {self.stats['old_embeds_removed']}")
        report.append(f"Files skipped: {self.stats['files_skipped']}")
        
        return "\n".join(report)


def inject_embeds(projects_dir: Path, dry_run: bool = False, verbose: bool = False) -> tuple[dict, List[str]]:
    """
    Main function to inject embeds into documentation
    
    Args:
        projects_dir: Directory containing Godot projects
        dry_run: If True, don't actually modify files
        verbose: Whether to show detailed progress
        
    Returns:
        Tuple of (stats_dict, errors_list)
    """
    progress = ProgressReporter(verbose=verbose)
    injector = EmbedInjector(progress)
    
    if verbose:
        progress.info(f"🔍 Processing embeds in: {projects_dir}")
    
    # Inject embeds
    stats = injector.inject_embeds_into_projects(projects_dir, dry_run=dry_run)
    
    # Show report if verbose
    if verbose:
        progress.info(injector.generate_report())
    
    return stats, []


if __name__ == "__main__":
    """Test the embed injector"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Inject embed markers into documentation')
    parser.add_argument('--config', '-c', default='../../build_config.json',
                       help='Path to build configuration file')
    parser.add_argument('--projects-dir', '-p', 
                       help='Override projects directory path')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = BuildSystemConfig.from_json_file(Path(args.config))
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        exit(1)
    
    # Determine projects directory
    if args.projects_dir:
        projects_dir = Path(args.projects_dir)
    else:
        projects_dir = Path(args.config).parent / config.structure.projects_dir
    
    # Inject embeds
    stats, errors = inject_embeds(
        projects_dir, dry_run=args.dry_run, verbose=args.verbose
    )
    
    if errors:
        print(f"\n❌ Embed injection completed with {len(errors)} errors:")
        for error in errors:
            print(f"  - {error}")
        exit(1)
    else:
        print(f"✅ Successfully processed {stats['files_processed']} files")
        print(f"   - Embeds added: {stats['embeds_added']}")
        print(f"   - Old embeds removed: {stats['old_embeds_removed']}")
