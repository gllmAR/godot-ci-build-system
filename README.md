# Universal Godot Build System

A comprehensive, modular build system for Godot projects that can be extracted and reused across different repositories. This system encapsulates all CI/CD logic and provides a universal interface for building, testing, and deploying Godot documentation sites.

## Features

### Core Building
- **Project Export**: Automatically exports Godot projects to web format
- **Documentation Generation**: Creates interactive documentation with embedded games
- **Parallel Processing**: Builds multiple projects simultaneously
- **Smart Caching**: Avoids unnecessary rebuilds
- **Progress Tracking**: Real-time build progress and statistics

### Environment Management
- **Godot Installation**: Automatically downloads and installs Godot engine
- **Template Management**: Handles export templates for all Godot versions (stable, beta, alpha)
- **Environment Verification**: Validates Godot installation and templates
- **Cross-Platform**: Works on Linux, macOS, and Windows

### Change Detection
- **Git Integration**: Detects changes using Git diff
- **Filesystem Monitoring**: Tracks file changes with hashing
- **Incremental Builds**: Only rebuilds changed projects
- **Smart Dependencies**: Rebuilds affected projects when build system changes

### Artifact Management
- **Deployment Preparation**: Packages builds for deployment
- **Artifact Validation**: Ensures all required files are present
- **Cleanup Management**: Removes unwanted files before packaging
- **Size Optimization**: Filters out development artifacts

### CI/CD Integration
- **Universal Interface**: Single entry point for all build operations
- **Environment Encapsulation**: All setup logic contained in build system
- **Artifact Packaging**: Ready-to-deploy output generation
- **Validation Pipeline**: Comprehensive build verification

## Quick Start

### Basic Usage

```bash
# Build everything (auto-detects changes)
python godot-ci-build-system/build.py

# Set up Godot environment
python godot-ci-build-system/build.py setup --godot-version 4.5-beta1

# Build with specific options
python godot-ci-build-system/build.py build --jobs 4 --verbose

# Prepare deployment artifact
python godot-ci-build-system/build.py artifact --artifact-output ./deploy
```

### Environment Setup

```bash
# Install Godot and export templates
python godot-ci-build-system/build.py setup --godot-version 4.5-beta1

# Verify installation
python godot-ci-build-system/build.py verify

# Force reinstall
python godot-ci-build-system/build.py setup --godot-version 4.5-beta1 --force-rebuild
```

### Change Detection

```bash
# Build only changed projects
python godot-ci-build-system/build.py build

# Force rebuild everything
python godot-ci-build-system/build.py build --force-rebuild

# Preview what would be built
python godot-ci-build-system/build.py --preview

# Use filesystem change detection instead of Git
python godot-ci-build-system/build.py build --no-change-detection
```

## Command Reference

### Targets

- `all` (default): Build projects and generate documentation
- `build`: Build projects only
- `docs`: Generate documentation only
- `setup`: Set up Godot environment
- `verify`: Verify Godot environment
- `artifact`: Prepare deployment artifact
- `clean`: Clean build artifacts

### Options

**Configuration:**
- `--config FILE`: Use custom configuration file
- `--projects-dir DIR`: Override projects directory
- `--godot-version VER`: Specify Godot version

**Build Control:**
- `--jobs N`: Number of parallel jobs
- `--force-rebuild`: Force rebuild all projects
- `--dry-run`: Show what would be built
- `--preview`: Preview build plan

**Environment:**
- `--setup-godot`: Set up Godot environment
- `--verify-environment`: Verify environment

**Change Detection:**
- `--base-ref REF`: Base reference for Git diff (default: HEAD~1)
- `--no-change-detection`: Skip change detection

**Artifacts:**
- `--prepare-artifact`: Prepare deployment artifact
- `--artifact-output DIR`: Output directory for artifacts

**Output:**
- `--verbose`: Enable verbose output
- `--progress`: Show detailed progress

## Architecture

### Modules

1. **Environment Manager** (`tools/environment_manager.py`)
   - Godot binary installation
   - Export template management
   - Environment validation
   - Cross-platform support

2. **Artifact Manager** (`tools/artifact_manager.py`)
   - Build artifact cleanup
   - Deployment preparation
   - Validation pipeline
   - Size optimization

3. **Change Detector** (`tools/change_detector.py`)
   - Git-based change detection
   - Filesystem monitoring
   - Smart dependency analysis
   - Incremental build logic

4. **Progress Reporter** (`tools/progress_reporter.py`)
   - Real-time progress tracking
   - Build statistics
   - Visual feedback
   - Performance metrics

## CI/CD Integration

### GitHub Actions

The build system provides a complete CI/CD solution. Here's a minimal workflow:

```yaml
name: Build with Universal System
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Setup Godot environment
        run: python build_system/build.py setup --godot-version 4.5-beta1
      
      - name: Build all projects
        run: python build_system/build.py all --verbose
      
      - name: Prepare deployment
        run: python build_system/build.py artifact --artifact-output ./deploy
      
      - name: Deploy to Pages
        uses: actions/upload-pages-artifact@v3
        with:
          path: ./deploy
```

**Benefits:**
- **Thin Workflows**: CI files become simple wrappers
- **Environment Independence**: Works across different CI providers
- **Reproducible Builds**: Same behavior locally and in CI
- **Error Handling**: Comprehensive validation and reporting

## Extraction as Submodule

To use this build system in another repository:

1. **Add as submodule:**
   ```bash
   git submodule add https://github.com/your-org/godot-examples-build-system.git build_system
   ```

2. **Create project configuration:**
   ```bash
   cp build_system/build_config.example.json build_config.json
   # Edit build_config.json for your project
   ```

3. **Create wrapper script:**
   ```bash
   #!/bin/bash
   python build_system/build.py "$@"
   ```

4. **Update CI workflow:**
   ```yaml
   # Replace complex CI logic with:
   - name: Build everything
     run: ./build.sh all --verbose
   ```

This build system is designed to be extracted as a reusable submodule.
