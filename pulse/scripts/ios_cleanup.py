#!/usr/bin/env python3
"""
iOS Project Cleanup Script
Removes temporary/generated files that shouldn't be in repos.

SAFE TO DELETE:
- claude-progress.txt (session logs)
- preflight_false_positives.json (temp QA)
- ui_audit_report.json (temp QA)
- qa_checklist.json (temp QA)
- qa-fixes.txt (temp QA)
- SESSION_*.md, TESTING_*.md (temp docs)
- *.backup, *.bak, *.old, *.tmp
- .DS_Store
- DerivedData/ folders
- Duplicate PaywallView.swift/SubscriptionManager.swift in root (if exists in app folder)

KEEP:
- feature_list.json (tracking)
- app_spec.txt (specifications)
- app_store_submission.txt (reference)
- README.md
- init.sh (setup scripts)
- update_tag.sh
"""

import os
import sys
from pathlib import Path
import shutil

IOS_DIR = Path.home() / "Documents" / "iOS"

# Files safe to delete
TEMP_FILES = [
    "claude-progress.txt",
    "preflight_false_positives.json",
    "ui_audit_report.json",
    "qa_checklist.json",
    "qa-fixes.txt",
]

# Patterns for temp files
TEMP_PATTERNS = [
    "SESSION_*.md",
    "TESTING_*.md",
    "*.backup",
    "*.bak",
    "*.old",
    "*.tmp",
    ".DS_Store",
]

def find_duplicate_swift_files(project_path: Path) -> list:
    """Find PaywallView.swift and SubscriptionManager.swift duplicates."""
    duplicates = []
    for filename in ["PaywallView.swift", "SubscriptionManager.swift"]:
        root_file = project_path / filename
        if root_file.exists():
            # Check if there's also one inside a subfolder
            for subdir in project_path.iterdir():
                if subdir.is_dir() and not subdir.name.startswith('.'):
                    nested = subdir / filename
                    if nested.exists():
                        duplicates.append(root_file)
                        break
    return duplicates

def scan_project(project_path: Path, dry_run: bool = True) -> dict:
    """Scan a single project for cleanup candidates."""
    results = {"delete": [], "keep": [], "duplicates": []}
    
    # Check temp files
    for filename in TEMP_FILES:
        filepath = project_path / filename
        if filepath.exists():
            results["delete"].append(filepath)
    
    # Check temp patterns
    for pattern in TEMP_PATTERNS:
        for filepath in project_path.glob(pattern):
            results["delete"].append(filepath)
    
    # Check DerivedData
    derived = project_path / "DerivedData"
    if derived.exists():
        results["delete"].append(derived)
    
    # Check duplicate Swift files
    results["duplicates"] = find_duplicate_swift_files(project_path)
    
    return results

def scan_all(dry_run: bool = True):
    """Scan all iOS projects."""
    total_delete = []
    total_duplicates = []
    
    for project in sorted(IOS_DIR.iterdir()):
        if project.is_dir() and not project.name.startswith('.'):
            results = scan_project(project, dry_run)
            total_delete.extend(results["delete"])
            total_duplicates.extend(results["duplicates"])
    
    print(f"\n{'='*60}")
    print(f"CLEANUP SUMMARY")
    print(f"{'='*60}")
    
    if total_delete:
        print(f"\n📁 TEMP FILES TO DELETE ({len(total_delete)}):")
        for f in sorted(total_delete):
            size = f.stat().st_size if f.is_file() else sum(p.stat().st_size for p in f.rglob('*') if p.is_file())
            print(f"  {f.relative_to(IOS_DIR)} ({size:,} bytes)")
    
    if total_duplicates:
        print(f"\n⚠️  DUPLICATE SWIFT FILES IN ROOT ({len(total_duplicates)}):")
        print("  (These exist both in root AND in app subfolder)")
        for f in sorted(total_duplicates):
            print(f"  {f.relative_to(IOS_DIR)}")
    
    total_size = sum(
        (f.stat().st_size if f.is_file() else sum(p.stat().st_size for p in f.rglob('*') if p.is_file()))
        for f in total_delete
    )
    
    print(f"\n📊 TOTAL: {len(total_delete)} files/folders, {total_size:,} bytes")
    print(f"   + {len(total_duplicates)} duplicate Swift files")
    
    if dry_run:
        print(f"\n⚠️  DRY RUN - No files deleted")
        print(f"   Run with --delete to actually remove files")
    
    return total_delete, total_duplicates

def delete_files(files: list, duplicates: list):
    """Actually delete the files."""
    deleted = 0
    for f in files:
        try:
            if f.is_dir():
                shutil.rmtree(f)
            else:
                f.unlink()
            deleted += 1
            print(f"  ✓ Deleted: {f.relative_to(IOS_DIR)}")
        except Exception as e:
            print(f"  ✗ Error: {f.relative_to(IOS_DIR)} - {e}")
    
    for f in duplicates:
        try:
            f.unlink()
            deleted += 1
            print(f"  ✓ Deleted duplicate: {f.relative_to(IOS_DIR)}")
        except Exception as e:
            print(f"  ✗ Error: {f.relative_to(IOS_DIR)} - {e}")
    
    print(f"\n✅ Deleted {deleted} items")

if __name__ == "__main__":
    dry_run = "--delete" not in sys.argv
    
    print("iOS Project Cleanup Scanner")
    print(f"Scanning: {IOS_DIR}")
    
    files, duplicates = scan_all(dry_run)
    
    if not dry_run and (files or duplicates):
        confirm = input("\nConfirm deletion? (yes/no): ")
        if confirm.lower() == "yes":
            delete_files(files, duplicates)
        else:
            print("Cancelled.")
