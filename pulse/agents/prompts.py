"""
Prompt Loading Utilities for iOS Apps
=====================================

Functions for loading prompt templates from the prompts directory.
"""

import shutil
from pathlib import Path
from typing import Optional


PROMPTS_DIR = Path(__file__).parent / "prompts"
IOS_DIR = Path.home() / "Documents" / "iOS"


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = PROMPTS_DIR / f"{name}.md"
    return prompt_path.read_text()


def get_initializer_prompt() -> str:
    """Load the initializer prompt for iOS apps."""
    return load_prompt("initializer_prompt")


def get_coding_prompt() -> str:
    """Load the coding agent prompt for iOS apps."""
    return load_prompt("coding_prompt")


def get_ios_apps() -> list[str]:
    """Get list of all iOS app directories."""
    if not IOS_DIR.exists():
        return []
    
    apps = []
    for item in IOS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            # Check if it has an .xcodeproj
            has_xcode = any(f.suffix == ".xcodeproj" for f in item.iterdir() if f.is_dir())
            if has_xcode:
                apps.append(item.name)
    return sorted(apps)


def get_app_path(app_name: str) -> Path:
    """Get the full path to an iOS app directory."""
    return IOS_DIR / app_name


def has_feature_list(project_dir: Path) -> bool:
    """Check if project has feature_list.json."""
    return (project_dir / "feature_list.json").exists()


def has_app_spec(project_dir: Path) -> bool:
    """Check if project has MASTER.md."""
    return (project_dir / "MASTER.md").exists()


def get_design_guide(project_dir: Path) -> Optional[str]:
    """Read DESIGN_GUIDE.md if it exists."""
    guide_path = project_dir / "DESIGN_GUIDE.md"
    if guide_path.exists():
        return guide_path.read_text()
    return None


def copy_spec_to_project(project_dir: Path) -> None:
    """Copy the app spec file into the project directory for the agent to read."""
    spec_source = Path.home() / "Documents" / "iOS" / "dev-docs" / "MASTER.md"
    spec_dest = project_dir / "MASTER.md"
    if spec_source.exists() and not spec_dest.exists():
        shutil.copy(spec_source, spec_dest)
        print(f"Copied MASTER.md to {project_dir}")
