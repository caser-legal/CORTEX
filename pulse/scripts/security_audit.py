#!/usr/bin/env python3
"""
Security Audit - Standalone security scanner for iOS projects

Usage:
    security -p ~/Documents/iOS/MyApp
    python3 ~/.codex/security_audit.py -p /path/to/project
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "agents"))

from security import run_project_security_audit


def main():
    parser = argparse.ArgumentParser(
        description="Security Audit - Scan iOS projects for dangerous patterns"
    )
    parser.add_argument(
        "--project-dir", "-p",
        type=Path,
        default=Path.cwd(),
        help="Directory to scan (default: current directory)",
    )
    
    args = parser.parse_args()
    project_dir = args.project_dir.resolve()
    
    print("\n" + "=" * 70)
    print("  🔒 SECURITY AUDIT")
    print("=" * 70)
    print(f"\nScanning: {project_dir}\n")
    
    results = run_project_security_audit(str(project_dir))
    
    print("\n" + "=" * 70)
    if results["errors"]:
        print("  ❌ AUDIT FAILED")
        sys.exit(1)
    elif results["warnings"]:
        print("  ⚠️  AUDIT PASSED WITH WARNINGS")
        sys.exit(0)
    else:
        print("  ✅ AUDIT PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
