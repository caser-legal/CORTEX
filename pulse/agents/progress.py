"""
Progress Tracking Utilities for iOS Apps
========================================

Functions for tracking and displaying progress of the iOS autonomous coding agent.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional


def count_passing_tests(project_dir: Path) -> tuple[int, int]:
    """
    Count passing and total tests in feature_list.json.

    Args:
        project_dir: Directory containing feature_list.json

    Returns:
        (passing_count, total_count)
    """
    tests_file = project_dir / "feature_list.json"

    if not tests_file.exists():
        return 0, 0

    try:
        with open(tests_file, "r") as f:
            data = json.load(f)

        # Handle structure with test_suite
        if isinstance(data, dict) and "test_suite" in data:
            tests = data["test_suite"]
            total = len(tests)
            passing = sum(1 for test in tests if isinstance(test, dict) and test.get("passes", False))
        else:
            # Fallback for flat list structure
            tests = data if isinstance(data, list) else []
            total = len(tests)
            passing = sum(1 for test in tests if isinstance(test, dict) and test.get("passes", False))

        return passing, total
    except (json.JSONDecodeError, IOError):
        return 0, 0


def get_app_name(project_dir: Path) -> str:
    """Get the app name from the project directory."""
    return project_dir.name


def get_xcode_project(project_dir: Path) -> Optional[Path]:
    """Find the .xcodeproj in the project directory."""
    for item in project_dir.iterdir():
        if item.suffix == ".xcodeproj":
            return item
    return None


def check_build_status(project_dir: Path) -> bool:
    """
    Check if the iOS app builds successfully.
    
    Returns:
        True if build succeeds, False otherwise
    """
    xcodeproj = get_xcode_project(project_dir)
    if not xcodeproj:
        return False
    
    app_name = get_app_name(project_dir)
    
    try:
        result = subprocess.run(
            [
                "xcodebuild",
                "-project", str(xcodeproj),
                "-scheme", app_name,
                "-destination", "generic/platform=iOS",
                "-configuration", "Release",
                "build"
            ],
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def print_session_header(session_num: int, is_initializer: bool) -> None:
    """Print a formatted header for the session."""
    session_type = "INITIALIZER" if is_initializer else "iOS CODING AGENT"

    print("\n" + "=" * 70)
    print(f"  SESSION {session_num}: {session_type}")
    print("=" * 70)
    print()


def print_progress_summary(project_dir: Path) -> None:
    """Print a summary of current progress."""
    passing, total = count_passing_tests(project_dir)
    app_name = get_app_name(project_dir)

    print(f"\n📱 App: {app_name}")
    
    if total > 0:
        percentage = (passing / total) * 100
        bar_length = 30
        filled = int(bar_length * passing / total)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"Progress: [{bar}] {passing}/{total} ({percentage:.1f}%)")
        
        # Warn if suspiciously low test count
        if total < 150:
            print(f"⚠️  WARNING: Only {total} tests (expected 150+)")
    else:
        print("Progress: feature_list.json not yet created")


def get_failing_tests(project_dir: Path) -> list[dict]:
    """Get list of failing tests."""
    tests_file = project_dir / "feature_list.json"
    
    if not tests_file.exists():
        return []
    
    try:
        with open(tests_file, "r") as f:
            data = json.load(f)
        
        # Handle nested structure with categories
        if isinstance(data, dict) and "categories" in data:
            all_tests = []
            for category in data["categories"]:
                if isinstance(category, dict) and "tests" in category:
                    all_tests.extend(category["tests"])
            return [t for t in all_tests if isinstance(t, dict) and not t.get("passes", False)]
        else:
            # Fallback for flat list structure
            tests = data if isinstance(data, list) else []
            return [t for t in tests if isinstance(t, dict) and not t.get("passes", False)]
    except (json.JSONDecodeError, IOError):
        return []


def get_next_feature(project_dir: Path) -> Optional[dict]:
    """Get the next feature to implement (first failing test)."""
    failing = get_failing_tests(project_dir)
    return failing[0] if failing else None
