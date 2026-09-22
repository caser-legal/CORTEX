#!/usr/bin/env python3
"""
Memory Sync - Unified memory update system for closed-loop learning
====================================================================

Called at session boundaries to:
1. Pre-session: Populate anchor.md and session_state.json with project info
2. Post-session: Record outcomes, update semantic.json with learned facts
3. Sync build_intelligence patterns into PULSE semantic tier

Usage:
    python3 memory_sync.py pre /path/to/project   # Before session
    python3 memory_sync.py post /path/to/project  # After session
    python3 memory_sync.py sync                   # Sync all memory files
"""

import fcntl
import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

GLOBAL_MEMORY = Path.home() / ".codex" / "memory"
BUILD_PATTERNS = GLOBAL_MEMORY / "build_patterns.json"
FEATURE_PATTERNS = GLOBAL_MEMORY / "feature_patterns.json"
SESSION_OBSERVATIONS = GLOBAL_MEMORY / "session_observations.json"


@contextmanager
def file_lock(filepath: Path):
    """Lock file for safe concurrent access across multiple agents."""
    lock_path = filepath.with_suffix(filepath.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()

def get_memory_dir(project_dir: Path) -> Path:
    """Get memory directory - ALWAYS project-local for session isolation."""
    local = project_dir / ".codex" / "memory"
    local.mkdir(parents=True, exist_ok=True)  # Create if missing
    return local


def get_project_info(project_dir: Path) -> dict:
    """Extract project information."""
    info = {
        "name": project_dir.name,
        "path": str(project_dir),
        "timestamp": datetime.now().isoformat()
    }
    
    # Get feature counts
    feature_list = project_dir / "feature_list.json"
    if feature_list.exists():
        try:
            with open(feature_list) as f:
                data = json.load(f)
            features = data.get("test_suite", data) if isinstance(data, dict) else data
            info["total_features"] = len(features)
            info["passing_features"] = sum(1 for f in features if isinstance(f, dict) and f.get("passes"))
            info["failing_features"] = info["total_features"] - info["passing_features"]
        except:
            pass
    
    # Get git info
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=project_dir
        )
        if result.returncode == 0:
            info["git_commit"] = result.stdout.strip()
    except:
        pass
    
    return info


def update_anchor_pre_session(project_dir: Path):
    """Update anchor.md with current project info before session."""
    memory_dir = get_memory_dir(project_dir)
    anchor_path = memory_dir / "anchor.md"
    info = get_project_info(project_dir)
    
    if not anchor_path.exists():
        # Create anchor.md from template
        template = f"""# ANCHOR (TIER 0 - Never Compress)
<!-- Position: 0-5% of context | Attention: ~95% -->

## Current Project
- Name: {info["name"]}
- Path: {info["path"]}

## Critical Decisions
<!-- Format: [DATE] Decision: reason -->

## Active Constraints
<!-- MUST/NEVER rules that cannot be forgotten -->

## Known Blockers
<!-- Current impediments to progress -->

## Session Continuity
<!-- Key info for next session pickup -->
- Last updated: {info["timestamp"]}
- Features: {info.get("passing_features", 0)}/{info.get("total_features", 0)} passing
- Git: {info.get("git_commit", "unknown")}
"""
        anchor_path.write_text(template)
        print(f"✅ Created anchor.md for project: {info['name']}")
        return
    
    info = get_project_info(project_dir)
    lines = anchor_path.read_text().split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        if line.startswith('- Name: '):
            new_lines.append(f'- Name: {info["name"]}')
        elif line.startswith('- Path: '):
            new_lines.append(f'- Path: {info["path"]}')
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Update session continuity section
    continuity = f"""## Session Continuity
<!-- Key info for next session pickup -->
- Last updated: {info["timestamp"]}
- Features: {info.get("passing_features", 0)}/{info.get("total_features", 0)} passing
- Git: {info.get("git_commit", "unknown")}
"""
    
    if "## Session Continuity" in content:
        # Find and replace the section
        start = content.find("## Session Continuity")
        end = content.find("\n## ", start + 1)
        if end == -1:
            end = len(content)
        content = content[:start] + continuity + content[end:]
    else:
        content += "\n" + continuity
    
    anchor_path.write_text(content)
    print(f"✅ Updated anchor.md with project: {info['name']}")


def update_session_state_pre(project_dir: Path):
    """Update session_state.json before session."""
    memory_dir = get_memory_dir(project_dir)
    state_path = memory_dir / "session_state.json"
    
    info = get_project_info(project_dir)
    
    state = {
        "project": info["name"],
        "project_path": info["path"],
        "session_start": info["timestamp"],
        "features_at_start": info.get("passing_features", 0),
        "total_at_start": info.get("total_features", 0),
        "features_completed_this_session": [],
        "current_task": "",
        "build_results": [],
        "errors_encountered": [],
        "last_3_turns": [],
        "context_usage_percent": 0
    }
    
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)
    
    print(f"✅ Updated session_state.json")


def update_session_state_post(project_dir: Path, build_success: bool = None):
    """Update session_state.json after session with outcomes."""
    memory_dir = get_memory_dir(project_dir)
    state_path = memory_dir / "session_state.json"
    
    if not state_path.exists():
        return
    
    with open(state_path) as f:
        state = json.load(f)
    
    info = get_project_info(project_dir)
    
    # Calculate features completed this session
    features_at_start = state.get("features_at_start", 0)
    features_now = info.get("passing_features", 0)
    features_completed = max(0, features_now - features_at_start)
    
    state["session_end"] = info["timestamp"]
    state["features_at_end"] = features_now
    state["total_at_end"] = info.get("total_features", 0)
    state["features_completed_count"] = features_completed
    
    if build_success is not None:
        state["build_results"].append({
            "timestamp": info["timestamp"],
            "success": build_success
        })
    
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)
    
    print(f"✅ Session complete: {features_completed} features implemented")


def sync_build_patterns_to_semantic():
    """Sync learned build patterns into semantic.json facts."""
    if not BUILD_PATTERNS.exists():
        return
    
    semantic_path = GLOBAL_MEMORY / "semantic.json"
    if not semantic_path.exists():
        return
    
    with open(BUILD_PATTERNS) as f:
        build_data = json.load(f)
    
    with open(semantic_path) as f:
        semantic = json.load(f)
    
    # Extract successful fix patterns as facts
    patterns = build_data.get("patterns", {})
    new_facts = []
    
    for error_type, data in patterns.items():
        if data.get("successes", 0) > 0 and data.get("fixes"):
            # Get most common fix
            from collections import Counter
            fix_counts = Counter(data["fixes"])
            best_fix = fix_counts.most_common(1)[0][0] if fix_counts else None
            if best_fix:
                fact = f"Build fix for {error_type}: {best_fix[:100]}"
                if fact not in semantic.get("facts", []):
                    new_facts.append(fact)
    
    if new_facts:
        semantic["facts"] = semantic.get("facts", []) + new_facts[:5]  # Limit to 5 new facts
        semantic["last_updated"] = datetime.now().isoformat()
        
        with file_lock(semantic_path):
            with open(semantic_path, 'w') as f:
                json.dump(semantic, f, indent=2)
        
        print(f"✅ Added {len(new_facts)} learned facts to semantic.json")


def sync_session_observations():
    """Sync session observations into learned insights."""
    if not SESSION_OBSERVATIONS.exists():
        return
    
    with open(SESSION_OBSERVATIONS) as f:
        obs = json.load(f)
    
    sessions = obs.get("sessions", [])
    if not sessions:
        return
    
    # Calculate aggregate stats
    total_features = sum(s.get("features_completed", 0) for s in sessions)
    total_errors = sum(len(s.get("errors_encountered", [])) for s in sessions)
    
    insights = {
        "generated_at": datetime.now().isoformat(),
        "total_sessions": len(sessions),
        "total_features_completed": total_features,
        "total_errors_encountered": total_errors,
        "avg_features_per_session": total_features / len(sessions) if sessions else 0,
        "recommendations": []
    }
    
    # Generate recommendations
    if insights["avg_features_per_session"] < 5:
        insights["recommendations"].append("Low feature velocity - consider breaking down tasks")
    
    if total_errors > total_features:
        insights["recommendations"].append("High error rate - review common error patterns")
    
    insights_path = GLOBAL_MEMORY / "learned_insights.json"
    with file_lock(insights_path):
        with open(insights_path, 'w') as f:
            json.dump(insights, f, indent=2)
    
    print(f"✅ Updated learned_insights.json")


def record_build_result(project_dir: Path, success: bool, output: str = ""):
    """Record a build result for learning."""
    memory_dir = get_memory_dir(project_dir)
    state_path = memory_dir / "session_state.json"
    
    if state_path.exists():
        with open(state_path) as f:
            state = json.load(f)
        
        state.setdefault("build_results", []).append({
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "output_snippet": output[:500] if output else ""
        })
        
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 memory_sync.py pre /path/to/project")
        print("  python3 memory_sync.py post /path/to/project")
        print("  python3 memory_sync.py sync")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "pre":
        if len(sys.argv) < 3:
            print("Usage: python3 memory_sync.py pre /path/to/project")
            sys.exit(1)
        project_dir = Path(sys.argv[2]).resolve()
        update_anchor_pre_session(project_dir)
        update_session_state_pre(project_dir)
        
    elif command == "post":
        if len(sys.argv) < 3:
            print("Usage: python3 memory_sync.py post /path/to/project")
            sys.exit(1)
        project_dir = Path(sys.argv[2]).resolve()
        build_success = "--build-success" in sys.argv
        build_fail = "--build-fail" in sys.argv
        
        if build_success:
            update_session_state_post(project_dir, True)
        elif build_fail:
            update_session_state_post(project_dir, False)
        else:
            update_session_state_post(project_dir)
        
        # Sync patterns after session
        sync_build_patterns_to_semantic()
        sync_session_observations()
        
    elif command == "sync":
        sync_build_patterns_to_semantic()
        sync_session_observations()
        print("✅ Memory sync complete")
        
    elif command == "build":
        # Record build result
        if len(sys.argv) < 4:
            print("Usage: python3 memory_sync.py build /path/to/project success|fail")
            sys.exit(1)
        project_dir = Path(sys.argv[2]).resolve()
        success = sys.argv[3] == "success"
        record_build_result(project_dir, success)
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
