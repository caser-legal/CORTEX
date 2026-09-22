#!/usr/bin/env python3
"""
Codex Autonomous Coding Agent
=============================

A harness for long-running autonomous coding with Codex CLI.
Implements the two-agent pattern (initializer + coding agent).

Usage:
    python autonomous.py --project-dir ~/Documents/iOS/MyApp
    python autonomous.py -p ~/Documents/iOS/MyApp --max-iterations 5
"""

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add agents directory to path for qa_checklist
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

try:
    from qa_checklist import count_qa_progress, run_auto_verification, reset_qa_checklist
except ImportError:
    def count_qa_progress(project_dir):
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
    
    def reset_qa_checklist(project_dir):
        pass


def get_stagger_delay(project_dir: Path) -> float:
    """Calculate a deterministic delay based on project path to stagger multiple agents."""
    path_hash = hashlib.md5(str(project_dir).encode()).hexdigest()
    delay = (int(path_hash[:4], 16) % 50) / 10.0
    return delay


def count_features(project_dir: Path) -> tuple[int, int]:
    """Count passing and total features in feature_list.json."""
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


def select_agent(project_dir: Path) -> str:
    """Select which agent to use based on project state."""
    passing, total = count_features(project_dir)
    
    # No feature_list.json or too few features -> initializer
    if total < 150:
        return "initializer"
    
    # All features passing and 300+ -> qa
    if passing >= 300 and passing == total:
        return "qa"
    
    # Otherwise -> coder
    return "coder"


def get_prompt(agent: str, project_dir: Path) -> str:
    """Get the prompt for the selected agent."""
    passing, total = count_features(project_dir)
    
    if agent == "initializer":
        app_spec = project_dir / "app_spec.txt"
        spec_content = ""
        if app_spec.exists():
            spec_content = f"\n\nApp spec:\n{app_spec.read_text()}"
        return f"Create feature_list.json with 300+ features for this iOS app.{spec_content}"
    
    elif agent == "qa":
        qa_verified, qa_total = count_qa_progress(project_dir)
        return f"Run QA verification on this completed iOS app. Currently {qa_verified}/{qa_total} QA checks verified. Fix any failing checks."
    
    else:  # coder
        return f"Implement features from feature_list.json. Currently {passing}/{total} passing. Target: 300+ passing features."


async def run_codex(project_dir: Path, agent: str, prompt: str) -> int:
    """Run Codex CLI with the specified prompt."""
    cmd = [
        "/opt/homebrew/bin/codex",
        "exec",
        "--model", "gpt-5.2",
        "-C", str(project_dir),
        "--dangerously-bypass-approvals-and-sandbox",
        prompt
    ]
    
    print(f"\n{'='*60}")
    print(f"Running: codex exec ({agent} mode)")
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


async def run_autonomous_agent(project_dir: Path, max_iterations: int = None):
    """Main autonomous agent loop."""
    iteration = 0
    
    print("\n" + "="*60)
    print("  CODEX AUTONOMOUS iOS DEVELOPMENT AGENT")
    print("="*60)
    print(f"  Project: {project_dir}")
    print("="*60 + "\n")
    
    while True:
        iteration += 1
        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            break
        
        # Check completion - need BOTH features AND QA complete
        passing, total = count_features(project_dir)
        qa_verified, qa_total = count_qa_progress(project_dir)
        verified_marker = project_dir / ".qa_verified"
        
        # Features complete check
        features_complete = passing >= 300 and passing == total
        
        # QA complete check (actual progress, not just marker)
        qa_complete = qa_total > 0 and qa_verified == qa_total
        
        if features_complete and qa_complete:
            # Truly complete - create marker if needed
            if not verified_marker.exists():
                create_qa_verified_marker(project_dir, qa_verified, qa_total, passing, total)
            print("\n" + "🌟"*20)
            print("✨ PROJECT FULLY COMPLETE! ✨")
            print("🌟"*20)
            break
        
        # If marker exists but QA not complete, remove premature marker
        if verified_marker.exists() and not qa_complete:
            print(f"\n⚠️  Found .qa_verified marker but QA is only {qa_verified}/{qa_total}")
            print("   Removing premature marker...")
            verified_marker.unlink()
        
        # Select agent and run
        agent = select_agent(project_dir)
        prompt = get_prompt(agent, project_dir)
        
        print(f"\n[Iteration {iteration}] Agent: {agent}, Features: {passing}/{total}, QA: {qa_verified}/{qa_total}")
        
        # If features complete but QA not, initialize QA checklist if needed
        if features_complete and not qa_complete:
            qa_checklist_path = project_dir / "qa_checklist.json"
            if not qa_checklist_path.exists():
                print("\n📋 Initializing QA checklist...")
                reset_qa_checklist(project_dir)
            run_auto_verification(project_dir)
        
        returncode = await run_codex(project_dir, agent, prompt)
        
        # After QA agent runs, check if QA is now complete
        if agent == "qa":
            run_auto_verification(project_dir)
            qa_verified, qa_total = count_qa_progress(project_dir)
            if qa_total > 0 and qa_verified == qa_total:
                create_qa_verified_marker(project_dir, qa_verified, qa_total, passing, total)
                print("\n" + "🌟"*20)
                print("✨ PROJECT FULLY COMPLETE! ✨")
                print("🌟"*20)
                break
        
        if returncode != 0:
            print(f"\nCodex exited with code {returncode}, retrying in 30s...")
            await asyncio.sleep(30)
        else:
            # Brief pause between iterations
            await asyncio.sleep(5)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Codex Autonomous Coding Agent")
    parser.add_argument("--project-dir", "-p", type=Path, default=Path.cwd(),
                        help="Project directory (default: current)")
    parser.add_argument("--max-iterations", "-n", type=int, default=None,
                        help="Maximum iterations (default: unlimited)")
    return parser.parse_args()


def main():
    args = parse_args()
    project_dir = args.project_dir.resolve()
    
    # Stagger start
    delay = get_stagger_delay(project_dir)
    if delay > 0:
        print(f"Staggering start by {delay:.1f}s...")
        time.sleep(delay)
    
    try:
        asyncio.run(run_autonomous_agent(project_dir, args.max_iterations))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")


if __name__ == "__main__":
    main()
