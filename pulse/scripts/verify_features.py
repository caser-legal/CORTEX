#!/usr/bin/env python3
"""
Feature Verification Script
===========================

The ONLY reliable verification is: DOES IT BUILD?

This script:
1. Checks if project has Swift files (basic sanity)
2. Checks for TODO/FIXME stubs (potential incomplete code)
3. Builds the project (the real test)

If build succeeds → Code compiles, features are at least syntactically correct
If build fails → Code is broken, nothing works

We do NOT try to guess if features are "really" implemented by keyword matching.
That's the agent's job to verify before marking passing.

Usage:
    python verify_features.py [project_dir]           # Quick (no build)
    python verify_features.py [project_dir] --full    # Full (with build)
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def load_feature_counts(project_dir: Path) -> Tuple[int, int]:
    """Load feature_list.json. Returns (passing, total)."""
    tests_file = project_dir / "feature_list.json"
    if not tests_file.exists():
        return 0, 0
    
    try:
        with open(tests_file) as f:
            data = json.load(f)
        
        if isinstance(data, dict) and "test_suite" in data:
            features = data["test_suite"]
        elif isinstance(data, list):
            features = data
        else:
            features = []
        
        total = len(features)
        passing = sum(1 for f in features if f.get("passes", False))
        return passing, total
    except:
        return 0, 0


def count_swift_files(project_dir: Path) -> int:
    """Count Swift files in project."""
    count = 0
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['build', 'DerivedData', 'Pods']]
        for f in files:
            if f.endswith('.swift'):
                count += 1
    return count


def find_stubs(project_dir: Path) -> List[str]:
    """Find files with TODO/FIXME markers."""
    stub_patterns = [
        r'//\s*TODO',
        r'//\s*FIXME',
    ]
    
    files_with_stubs = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['build', 'DerivedData', 'Pods']]
        for f in files:
            if f.endswith('.swift'):
                try:
                    code = Path(root, f).read_text()
                    for pattern in stub_patterns:
                        if re.search(pattern, code, re.IGNORECASE):
                            files_with_stubs.append(f)
                            break
                except:
                    pass
    
    return list(set(files_with_stubs))


def build_project(project_dir: Path) -> Tuple[bool, str]:
    """Build the project. Returns (success, message)."""
    xcodeproj = None
    for item in project_dir.iterdir():
        if item.suffix == ".xcodeproj":
            xcodeproj = item
            break
    
    if not xcodeproj:
        return False, "No .xcodeproj found"
    
    scheme = xcodeproj.stem
    
    try:
        result = subprocess.run(
            [
                "xcodebuild",
                "-project", str(xcodeproj),
                "-scheme", scheme,
                "-destination", "generic/platform=iOS",
                "-configuration", "Release",
                "build"
            ],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=project_dir
        )
        
        if result.returncode == 0:
            return True, "BUILD SUCCEEDED"
        else:
            # Find first error
            for line in result.stdout.split('\n'):
                if 'error:' in line.lower():
                    return False, f"BUILD FAILED: {line[:100]}"
            return False, "BUILD FAILED"
    except subprocess.TimeoutExpired:
        return False, "BUILD TIMEOUT (>5 min)"
    except Exception as e:
        return False, f"BUILD ERROR: {e}"


def main():
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1]).resolve()
    else:
        project_dir = Path.cwd()
    
    do_build = "--full" in sys.argv
    
    print(f"\n{'=' * 60}")
    print("  FEATURE VERIFICATION")
    print(f"{'=' * 60}")
    print(f"\nProject: {project_dir.name}")
    
    # Feature counts
    passing, total = load_feature_counts(project_dir)
    print(f"\n📊 Features: {passing}/{total} marked passing")
    
    # Swift file count
    swift_count = count_swift_files(project_dir)
    if swift_count == 0:
        print("❌ NO Swift files found")
        sys.exit(1)
    print(f"✅ {swift_count} Swift files found")
    
    # Stub check
    stubs = find_stubs(project_dir)
    if stubs:
        print(f"⚠️  {len(stubs)} files with TODO/FIXME:")
        for s in stubs[:5]:
            print(f"   • {s}")
        if len(stubs) > 5:
            print(f"   ... and {len(stubs) - 5} more")
    else:
        print("✅ No TODO/FIXME markers found")
    
    # Build (the real test)
    if do_build:
        print(f"\n🔨 Building project...")
        build_ok, build_msg = build_project(project_dir)
        print(f"{'✅' if build_ok else '❌'} {build_msg}")
        
        if not build_ok:
            print("\n" + "=" * 50)
            print("❌ VERIFICATION FAILED - Build broken")
            sys.exit(1)
    else:
        print(f"\n⏭️  Build skipped (use --full to verify)")
    
    # Summary
    print("\n" + "=" * 50)
    print("✅ VERIFICATION PASSED")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
