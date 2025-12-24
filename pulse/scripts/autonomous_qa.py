#!/usr/bin/env python3
"""
Codex Autonomous QA Agent
=========================

Runs QA verification on completed iOS apps (300+ passing features).

Usage:
    python autonomous_qa.py --project-dir ~/Documents/iOS/MyApp
"""

import argparse
import asyncio
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

# Add agents directory to path for qa_checklist
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

try:
    from qa_checklist import count_qa_progress, run_auto_verification
except ImportError:
    def count_qa_progress(project_dir):
        """Fallback if qa_checklist not available."""
        checklist_path = project_dir / "qa_checklist.json"
        if not checklist_path.exists():
            return 0, 0
        try:
            with open(checklist_path) as f:
                data = json.load(f)
            total = len(data)
            verified = sum(1 for c in data if c.get("verified", False))
            return verified, total
        except:
            return 0, 0
    
    def run_auto_verification(project_dir):
        pass


def get_stagger_delay(project_dir: Path) -> float:
    path_hash = hashlib.md5(str(project_dir).encode()).hexdigest()
    delay = (int(path_hash[:4], 16) % 50) / 10.0
    return delay


def count_features(project_dir: Path) -> tuple[int, int]:
    feature_file = project_dir / "feature_list.json"
    if not feature_file.exists():
        return 0, 0
    try:
        with open(feature_file) as f:
            data = json.load(f)
        features = data.get("features", [])
        total = len(features)
        passing = sum(1 for f in features if f.get("passes", False))
        return passing, total
    except:
        return 0, 0


async def run_codex_qa(project_dir: Path) -> int:
    """Run Codex QA agent."""
    cmd = [
        "/opt/homebrew/bin/codex",
        "exec",
        "--model", "gpt-5.2",
        "-C", str(project_dir),
        "--dangerously-bypass-approvals-and-sandbox",
        "Run QA verification. Check UI compliance, accessibility, dark mode. Fix any failing QA checks."
    ]
    
    print(f"\n{'='*60}")
    print(f"Running: codex exec (QA mode)")
    print(f"Project: {project_dir}")
    print(f"{'='*60}\n")
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        print(line.decode(), end="")
    
    await proc.wait()
    return proc.returncode


def create_qa_verified_marker(project_dir: Path, qa_verified: int, qa_total: int, passing: int, total: int):
    """Create .qa_verified marker when QA is truly 100% complete."""
    verified_marker = project_dir / ".qa_verified"
    with open(verified_marker, "w") as f:
        f.write(f"QA verified: {qa_verified}/{qa_total} checks passed\n")
        f.write(f"Features: {passing}/{total} passing\n")
        f.write(f"Verified at: {datetime.now().isoformat()}\n")
    print("✅ Created .qa_verified marker")


async def run_autonomous_qa(project_dir: Path, max_iterations: int = None):
    """Main QA loop."""
    iteration = 0
    
    print("\n" + "="*60)
    print("  CODEX AUTONOMOUS QA AGENT")
    print("="*60)
    print(f"  Project: {project_dir}")
    print("="*60 + "\n")
    
    # Run auto-verification to get current QA state
    run_auto_verification(project_dir)
    
    while True:
        iteration += 1
        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            break
        
        passing, total = count_features(project_dir)
        qa_verified, qa_total = count_qa_progress(project_dir)
        verified_marker = project_dir / ".qa_verified"
        
        # Check if QA is actually 100% complete (not just marker exists)
        if qa_total > 0 and qa_verified == qa_total:
            # QA is truly complete
            print(f"\n✅ QA verification complete ({qa_verified}/{qa_total})")
            if not verified_marker.exists():
                create_qa_verified_marker(project_dir, qa_verified, qa_total, passing, total)
            print("\n" + "🌟"*20)
            print("✨ QA COMPLETE! ✨")
            print("🌟"*20)
            break
        elif verified_marker.exists():
            # Marker exists but QA is NOT 100% - this is the bug!
            # Delete the premature marker and continue with QA
            print(f"\n⚠️  Found .qa_verified marker but QA is only {qa_verified}/{qa_total}")
            print("   Removing premature marker and continuing QA verification...")
            verified_marker.unlink()
        
        print(f"\n[Iteration {iteration}] Features: {passing}/{total}, QA: {qa_verified}/{qa_total}")
        
        if passing < 300:
            print(f"App not ready for QA (need 300+ passing, have {passing})")
            break
        
        returncode = await run_codex_qa(project_dir)
        
        # Re-run auto-verification after QA session
        run_auto_verification(project_dir)
        
        # Check if QA is now complete
        qa_verified, qa_total = count_qa_progress(project_dir)
        if qa_total > 0 and qa_verified == qa_total:
            print(f"\n✅ QA verification complete ({qa_verified}/{qa_total})")
            create_qa_verified_marker(project_dir, qa_verified, qa_total, passing, total)
            print("\n" + "🌟"*20)
            print("✨ QA COMPLETE! ✨")
            print("🌟"*20)
            break
        
        if returncode != 0:
            print(f"\nCodex exited with code {returncode}, retrying in 30s...")
            await asyncio.sleep(30)
        else:
            await asyncio.sleep(5)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Codex Autonomous QA Agent")
    parser.add_argument("--project-dir", "-p", type=Path, default=Path.cwd())
    parser.add_argument("--max-iterations", "-n", type=int, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    project_dir = args.project_dir.resolve()
    
    delay = get_stagger_delay(project_dir)
    if delay > 0:
        print(f"Staggering start by {delay:.1f}s...")
        time.sleep(delay)
    
    try:
        asyncio.run(run_autonomous_qa(project_dir, args.max_iterations))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")


if __name__ == "__main__":
    main()
