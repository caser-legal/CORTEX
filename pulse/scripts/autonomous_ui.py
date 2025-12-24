#!/usr/bin/env python3
"""
Kiro AutoUI - Autonomous UI Designer Agent
==========================================

Final stage autonomous agent that transforms "working" iOS apps 
into "production-quality" apps ready for App Store submission.

Focuses on:
1. Visual polish - Every pixel matters
2. Functional correctness - Every feature works truthfully
3. Production readiness - App Store quality

Flow:
    autoui.py → autonomous_ui.py → agent_ui.py → ui agent
                                        ↓
                                   ui_audit.py (automated checks)
                                   progress.py (iOS tracking)

Example Usage:
    autoui -p ~/Documents/iOS/MyApp
    python autonomous_ui.py --project-dir ~/Documents/iOS/MyApp
    python autonomous_ui.py --project-dir ~/Documents/iOS/MyApp --max-iterations 5
"""

import argparse
import asyncio
import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

from agent_ui import run_autonomous_agent


def get_stagger_delay(project_dir: Path) -> float:
    """Calculate deterministic delay based on project path to stagger agents."""
    path_hash = hashlib.md5(str(project_dir).encode()).hexdigest()
    delay = (int(path_hash[:4], 16) % 50) / 10.0
    return delay


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="AutoUI - Final stage iOS UI Designer Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Polish an existing app
  python autonomous_ui.py --project-dir ~/Documents/iOS/MyApp

  # Limit iterations for testing
  python autonomous_ui.py --project-dir ~/Documents/iOS/MyApp --max-iterations 5

Usage:
  Run AFTER autoo and autoqa have completed their work.
  AutoUI takes working code and makes it production-ready.
        """,
    )

    parser.add_argument(
        "--project-dir", "-p",
        type=Path,
        default=Path.cwd(),
        help="Directory for the project (default: current directory)",
    )

    parser.add_argument(
        "--max-iterations", "-n",
        type=int,
        default=None,
        help="Maximum number of agent iterations (default: unlimited)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    project_dir = args.project_dir.resolve()

    delay = get_stagger_delay(project_dir)
    if delay > 0:
        print(f"Staggering start by {delay:.1f}s to prevent rate limiting...")
        time.sleep(delay)

    try:
        asyncio.run(
            run_autonomous_agent(
                project_dir=project_dir,
                max_iterations=args.max_iterations,
            )
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        print("To resume, run the same command again")
    except Exception as e:
        print(f"\nFatal error: {e}")
        raise


if __name__ == "__main__":
    main()
