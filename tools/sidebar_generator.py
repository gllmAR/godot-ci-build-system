#!/usr/bin/env python3
"""
Sidebar Generator for Godot Examples Documentation
Handles hierarchy, validates links, and provides comprehensive error reporting
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from project_config import BuildSystemConfig


@dataclass
class ProjectInfo:
    """Information about a discovered project or README"""
    name: str
    display_title: str
    path: Path
    relative_path: Path
    depth: int
    category: str
    has_readme: bool
    is_project: bool = True  # True for Godot projects, False for standalone READMEs
    readme_path: Optional[Path] = None
    parent_dirs: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.parent_dirs is None:
            self.parent_dirs = list(self.relative_path.parts[:-1])


class SidebarGenerator:
    """Enhanced sidebar generator with hierarchy support and validation"""
    
    def __init__(self, config: BuildSystemConfig):
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats = {
            'projects_found': 0,
            'projects_with_readme': 0,
            'categories': 0,
            'broken_links': 0
        }
    
    def extract_title_from_readme(self, readme_path: Path) -> Optional[str]:
        """
        Extract the first H1 title from a README.md file
        
        Args:
            readme_path: Path to the README.md file
            
        Returns:
            Extracted title or None if not found
        """
        try:
            content = readme_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('# '):
                    # Extract title after '# '
                    title = line[2:].strip()
                    if title:
                        return title
            
            return None
        except Exception as e:
            self.warnings.append(f"Failed to read README {readme_path}: {e}")
            return None
    
    def discover_projects_and_readmes(self, projects_dir: Path) -> List[ProjectInfo]:
        """
        Discover all Godot projects AND standalone README files with enhanced hierarchy analysis
        
        Args:
            projects_dir: Base directory to search for projects and READMEs
            
        Returns:
            List of ProjectInfo objects for both projects and standalone READMEs
        """
        if not projects_dir.exists():
            self.errors.append(f"Projects directory not found: {projects_dir}")
            return []
        
        projects = []
        
        # First, find all Godot projects
        project_files = list(projects_dir.rglob("project.godot"))
        
        for project_file in project_files:
            project_dir = project_file.parent
            relative_path = project_dir.relative_to(projects_dir)
            parts = relative_path.parts
            
            if not parts:
                self.warnings.append(f"Project at root level: {project_dir}")
                continue
            
            # Check for README and extract title
            readme_path = project_dir / "README.md"
            has_readme = readme_path.exists()
            display_title = parts[-1]  # Default to folder name
            
            if has_readme:
                extracted_title = self.extract_title_from_readme(readme_path)
                if extracted_title:
                    display_title = extracted_title
                else:
                    self.warnings.append(f"No H1 title found in README: {relative_path}")
            else:
                self.warnings.append(f"Missing README.md: {relative_path}")
            
            project_info = ProjectInfo(
                name=parts[-1],  # Last directory name (for technical use)
                display_title=display_title,  # Human-readable title from README
                path=project_dir,
                relative_path=relative_path,
                depth=len(parts) - 1,  # Depth beyond category
                category=parts[0],
                has_readme=has_readme,
                is_project=True,  # This is a Godot project
                readme_path=readme_path if has_readme else None
            )
            
            projects.append(project_info)
            self.stats['projects_found'] += 1
            if has_readme:
                self.stats['projects_with_readme'] += 1
        
        # Second, find standalone README files in directories without project.godot
        all_readme_files = list(projects_dir.rglob("README.md"))
        project_dirs = {p.path for p in projects}  # Set of directories that already have projects
        
        for readme_file in all_readme_files:
            readme_dir = readme_file.parent
            
            # Skip if this directory already has a project
            if readme_dir in project_dirs:
                continue
            
            # Skip if this is the root projects directory
            if readme_dir == projects_dir:
                continue
            
            relative_path = readme_dir.relative_to(projects_dir)
            parts = relative_path.parts
            
            if not parts:
                continue
            
            # Extract title from README
            extracted_title = self.extract_title_from_readme(readme_file)
            display_title = extracted_title if extracted_title else parts[-1]
            
            # Create a "virtual project" for this standalone README
            readme_info = ProjectInfo(
                name=parts[-1],  # Directory name
                display_title=display_title,  # Title from README
                path=readme_dir,
                relative_path=relative_path,
                depth=len(parts) - 1,  # Depth beyond category
                category=parts[0],
                has_readme=True,
                is_project=False,  # This is a standalone README, not a Godot project
                readme_path=readme_file
            )
            
            projects.append(readme_info)
            self.stats['projects_found'] += 1
            self.stats['projects_with_readme'] += 1
        
        return projects
        """
        Discover all Godot projects with enhanced hierarchy analysis
        
        Args:
            projects_dir: Base directory to search for projects
            
        Returns:
            List of ProjectInfo objects
        """
        if not projects_dir.exists():
            self.errors.append(f"Projects directory not found: {projects_dir}")
            return []
        
        project_files = list(projects_dir.rglob("project.godot"))
        projects = []
        
        for project_file in project_files:
            project_dir = project_file.parent
            relative_path = project_dir.relative_to(projects_dir)
            parts = relative_path.parts
            
            if not parts:
                self.warnings.append(f"Project at root level: {project_dir}")
                continue
            
            # Check for README and extract title
            readme_path = project_dir / "README.md"
            has_readme = readme_path.exists()
            display_title = parts[-1]  # Default to folder name
            
            if has_readme:
                extracted_title = self.extract_title_from_readme(readme_path)
                if extracted_title:
                    display_title = extracted_title
                else:
                    self.warnings.append(f"No H1 title found in README: {relative_path}")
            else:
                self.warnings.append(f"Missing README.md: {relative_path}")
            
            project_info = ProjectInfo(
                name=parts[-1],  # Last directory name (for technical use)
                display_title=display_title,  # Human-readable title from README
                path=project_dir,
                relative_path=relative_path,
                depth=len(parts) - 1,  # Depth beyond category
                category=parts[0],
                has_readme=has_readme,
                readme_path=readme_path if has_readme else None
            )
            
            projects.append(project_info)
            self.stats['projects_found'] += 1
            if has_readme:
                self.stats['projects_with_readme'] += 1
        
        return projects
    
    def group_projects_by_category(self, projects: List[ProjectInfo]) -> Dict[str, List[ProjectInfo]]:
        """
        Group projects by category with hierarchy preservation
        
        Args:
            projects: List of discovered projects
            
        Returns:
            Dictionary mapping categories to sorted project lists
        """
        categories = {}
        
        for project in projects:
            category = project.category
            if category not in categories:
                categories[category] = []
            categories[category].append(project)
        
        # Sort projects within each category by path for consistent hierarchy
        for category in categories:
            categories[category].sort(key=lambda p: p.relative_path)
        
        self.stats['categories'] = len(categories)
        return categories
    
    def build_hierarchy_tree(self, projects: List[ProjectInfo]) -> Dict:
        """
        Build a nested tree structure from flat project list
        
        Args:
            projects: List of projects in a category
            
        Returns:
            Nested dictionary representing the hierarchy
        """
        tree = {}
        
        for project in projects:
            parts = project.relative_path.parts
            current = tree
            
            # Navigate/create tree structure
            for i, part in enumerate(parts):
                if part not in current:
                    current[part] = {
                        'children': {},
                        'is_project': False,
                        'project_info': None
                    }
                
                # If this is the last part, it's a project
                if i == len(parts) - 1:
                    current[part]['is_project'] = True
                    current[part]['project_info'] = project
                
                current = current[part]['children']
        
        return tree
    
    def render_hierarchy_markdown(self, tree: Dict, base_path: str, depth: int = 0) -> str:
        """
        Render hierarchy tree as markdown with proper Docsify indentation
        
        Args:
            tree: Nested tree structure
            base_path: Base path for links
            depth: Current nesting depth
            
        Returns:
            Rendered markdown content compatible with Docsify
        """
        content = ""
        indent = "  " * depth
        
        for name, node in sorted(tree.items()):
            if node['is_project'] and node['project_info']:
                project = node['project_info']
                
                if project.has_readme:
                    link_path = f"/{base_path}/{project.relative_path}/README.md"
                    content += f"{indent}- [{project.display_title}]({link_path})\n"
                else:
                    # Still show the project but with a warning
                    content += f"{indent}- {project.display_title} ⚠️ (No README)\n"
                    self.stats['broken_links'] += 1
            
            # Render children with increased depth (Docsify style)
            if node['children']:
                child_content = self.render_hierarchy_markdown(
                    node['children'], base_path, depth + 1
                )
                content += child_content
        
        return content
    
    def validate_links(self, content: str, base_dir: Path) -> List[str]:
        """
        Validate all markdown links in the generated content
        
        Args:
            content: Generated sidebar content
            base_dir: Base directory for resolving relative paths
            
        Returns:
            List of broken link descriptions
        """
        broken_links = []
        
        # Extract all markdown links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(link_pattern, content)
        
        for link_text, link_path in matches:
            # Skip external links
            if link_path.startswith(('http://', 'https://', '#')):
                continue
            
            # Handle absolute paths (Docsify style)
            if link_path.startswith('/'):
                # For Docsify absolute paths, resolve relative to base_dir
                actual_path = base_dir / link_path[1:]  # Remove leading slash
            else:
                # Relative paths
                actual_path = base_dir / link_path
            
            # Check if file exists
            if not actual_path.exists():
                broken_links.append(f"'{link_text}' -> {link_path}")
        
        return broken_links
    
    def generate_sidebar(self, projects_dir: Path, use_hierarchy: bool = False) -> str:
        """
        Generate complete sidebar with hierarchy and validation
        
        Args:
            projects_dir: Directory containing Godot projects
            use_hierarchy: Whether to use hierarchical nesting (for complex projects)
            
        Returns:
            Generated sidebar markdown content compatible with Docsify
        """
        self.errors.clear()
        self.warnings.clear()
        self.stats = {
            'projects_found': 0,
            'projects_with_readme': 0,
            'categories': 0,
            'broken_links': 0
        }
        
        # Discover all projects and standalone READMEs
        projects = self.discover_projects_and_readmes(projects_dir)
        
        if not projects:
            return "No projects found.\n"
        
        # Group by category
        categories = self.group_projects_by_category(projects)
        
        # Generate content without title (Docsify handles titles separately)
        content = ""
        
        for category_name in sorted(categories.keys()):
            category_projects = categories[category_name]
            
            # Check if category has its own README
            category_readme_path = projects_dir / category_name / "README.md"
            if category_readme_path.exists():
                # Extract title from category README
                category_title = self.extract_title_from_readme(category_readme_path)
                if not category_title:
                    category_title = f"{category_name.upper()} Demos"
                
                # Make category a clickable link
                category_link = f"/{self.config.structure.projects_dir}/{category_name}/README.md"
                content += f"- [{category_title}]({category_link})\n\n"
            else:
                # Fallback to plain text if no category README
                content += f"- {category_name.upper()}\n\n"
            
            if use_hierarchy:
                # Build and render hierarchy (for complex nested structures)
                tree = self.build_hierarchy_tree(category_projects)
                category_content = self.render_hierarchy_markdown(
                    tree, self.config.structure.projects_dir, depth=1
                )
            else:
                # Simple flat structure (current format, but validated)
                # Check if category has its own README to avoid duplication
                category_readme_path = projects_dir / category_name / "README.md"
                has_category_readme = category_readme_path.exists()
                
                for project in sorted(category_projects, key=lambda p: p.display_title.lower()):
                    # Skip the category-level README if it's already used as category header
                    if (has_category_readme and 
                        len(project.relative_path.parts) == 1 and 
                        project.relative_path.parts[0] == category_name and
                        not project.is_project):  # Only skip standalone READMEs, not Godot projects
                        continue
                        
                    if project.has_readme:
                        link_path = f"/{self.config.structure.projects_dir}/{project.relative_path}/README.md"
                        content += f"  - [{project.display_title}]({link_path})\n"
                    else:
                        content += f"  - {project.display_title} ⚠️ (No README)\n"
                        self.stats['broken_links'] += 1
                category_content = ""
            
            content += category_content
            content += "\n"
        
        return content
    
    def generate_report(self) -> str:
        """Generate a status report of the sidebar generation"""
        report = []
        report.append("=== Sidebar Generation Report ===")
        report.append(f"Projects found: {self.stats['projects_found']}")
        report.append(f"Projects with README: {self.stats['projects_with_readme']}")
        report.append(f"Categories: {self.stats['categories']}")
        report.append(f"Broken links: {self.stats['broken_links']}")
        
        if self.errors:
            report.append("\n🚨 ERRORS:")
            for error in self.errors:
                report.append(f"  - {error}")
        
        if self.warnings:
            report.append("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                report.append(f"  - {warning}")
        
        return "\n".join(report)


def generate_sidebar(projects_dir: Path, config: BuildSystemConfig, 
                            validate: bool = True, verbose: bool = False,
                            use_hierarchy: bool = False) -> Tuple[str, List[str]]:
    """
    Generate improved sidebar with validation and error reporting
    
    Args:
        projects_dir: Directory containing Godot projects
        config: Build system configuration
        validate: Whether to validate generated links
        verbose: Whether to show detailed progress
        use_hierarchy: Whether to use hierarchical nesting for complex structures
        
    Returns:
        Tuple of (sidebar_content, errors)
    """
    generator = SidebarGenerator(config)
    
    if verbose:
        print(f"🔍 Scanning for projects in: {projects_dir}")
    
    # Generate sidebar
    content = generator.generate_sidebar(projects_dir, use_hierarchy=use_hierarchy)
    
    # Validate links if requested
    if validate:
        if verbose:
            print("🔗 Validating links...")
        broken_links = generator.validate_links(content, projects_dir.parent)
        if broken_links:
            generator.errors.extend([f"Broken link: {link}" for link in broken_links])
    
    # Show report if verbose
    if verbose:
        print(generator.generate_report())
    
    return content, generator.errors


if __name__ == "__main__":
    """Test the sidebar generator"""
    import argparse
    
    # Load config using the already imported BuildSystemConfig
    parser = argparse.ArgumentParser(description='Generate sidebar')
    parser.add_argument('--config', '-c', default='../../build_config.json',
                       help='Path to build configuration file')
    parser.add_argument('--output', '-o', default='../_sidebar_new.md',
                       help='Output file for generated sidebar')
    parser.add_argument('--validate', action='store_true',
                       help='Validate generated links')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--hierarchy', action='store_true',
                       help='Use hierarchical structure for nested projects')
    parser.add_argument('--projects-dir', '-p', 
                       help='Override projects directory path')
    
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
    
    # Generate sidebar
    content, errors = generate_sidebar(
        projects_dir, config, validate=args.validate, verbose=args.verbose,
        use_hierarchy=args.hierarchy
    )
    
    # Write output
    output_path = Path(args.output)
    output_path.write_text(content)
    
    if errors:
        print(f"\n❌ Generated sidebar with {len(errors)} errors:")
        for error in errors:
            print(f"  - {error}")
        exit(1)
    else:
        print(f"✅ Successfully generated sidebar: {output_path}")
