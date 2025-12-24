#!/usr/bin/env python3
"""
PULSE - Persistent Unified Learning Session Engine
Compression and Memory Management Script

Memory location priority:
1. ./.codex/memory/ (project-local, preferred)
2. ~/.codex/memory/ (global fallback)
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime

def get_memory_dir() -> Path:
    """Get memory directory - prefer project-local, fallback to global."""
    # Check for project-local .codex/memory/
    local = Path.cwd() / ".codex" / "memory"
    if local.exists():
        return local
    
    # Check parent directories (in case we're in a subdirectory)
    for parent in Path.cwd().parents:
        local = parent / ".codex" / "memory"
        if local.exists():
            return local
    
    # Fallback to global
    return Path.home() / ".codex" / "memory"

def init_project_memory(project_path: Path = None) -> Path:
    """Initialize project-local memory directory."""
    if project_path is None:
        project_path = Path.cwd()
    
    memory_dir = project_path / ".codex" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    
    # Create template files if they don't exist
    templates = {
        "anchor.md": """# ANCHOR (TIER 0 - Never Compress)
<!-- Position: 0-5% of context | Attention: ~95% -->

## Current Project
- Name: {name}
- Path: {path}

## Critical Decisions
<!-- Format: [DATE] Decision: reason -->

## Active Constraints
<!-- MUST/NEVER rules that cannot be forgotten -->

## Known Blockers
<!-- Current impediments to progress -->

## Session Continuity
<!-- Key info for next session pickup -->
""".format(name=project_path.name, path=str(project_path)),
        
        "semantic.json": json.dumps({
            "facts": [],
            "preferences": [],
            "patterns": [],
            "decisions": [],
            "entities": {"project": project_path.name},
            "last_updated": datetime.now().isoformat()
        }, indent=2),
        
        "procedural.md": """# PROCEDURAL (TIER 2 - Expendable)
<!-- Position: 15-40% of context (Dead Zone) | Attention: ~60% -->

## Code Patterns

## Build Commands

## Resolved Issues
""",
        
        "session_state.json": json.dumps({
            "project": project_path.name,
            "project_path": str(project_path),
            "features_completed_this_session": [],
            "current_task": "",
            "last_3_turns": [],
            "context_usage_percent": 0,
            "session_start": "",
            "last_compression": ""
        }, indent=2)
    }
    
    for filename, content in templates.items():
        filepath = memory_dir / filename
        if not filepath.exists():
            filepath.write_text(content)
    
    return memory_dir

MEMORY_DIR = get_memory_dir()

def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}

def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2))

def extract_decisions(text: str) -> list:
    """Extract critical decisions from conversation."""
    patterns = [
        r"(?:decided|choosing|will use|going with|selected)\s+(.+?)(?:\.|$)",
        r"MUST\s+(.+?)(?:\.|$)",
        r"NEVER\s+(.+?)(?:\.|$)",
        r"constraint:\s*(.+?)(?:\.|$)",
    ]
    decisions = []
    for p in patterns:
        decisions.extend(re.findall(p, text, re.IGNORECASE))
    return list(set(decisions))[:10]

def extract_facts(text: str) -> list:
    """Extract factual statements."""
    patterns = [
        r"(\w+)\s+(?:is|are|was|were)\s+(.+?)(?:\.|$)",
        r"(?:learned|discovered|found)\s+that\s+(.+?)(?:\.|$)",
    ]
    facts = []
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                facts.append(" ".join(m))
            else:
                facts.append(m)
    return list(set(facts))[:20]

def update_anchor(decisions: list, project: str = "", path: str = ""):
    """Update anchor.md with critical info."""
    anchor_path = MEMORY_DIR / "anchor.md"
    content = anchor_path.read_text() if anchor_path.exists() else ""
    
    if project:
        content = re.sub(r"- Name:.*", f"- Name: {project}", content)
    if path:
        content = re.sub(r"- Path:.*", f"- Path: {path}", content)
    
    if decisions:
        date = datetime.now().strftime("%Y-%m-%d")
        new_decisions = "\n".join([f"- [{date}] {d}" for d in decisions])
        if "## Critical Decisions" in content:
            content = content.replace(
                "## Critical Decisions\n<!-- Format: [DATE] Decision: reason -->",
                f"## Critical Decisions\n<!-- Format: [DATE] Decision: reason -->\n{new_decisions}"
            )
    
    anchor_path.write_text(content)

def update_semantic(facts: list, preferences: list = None):
    """Update semantic.json with extracted facts."""
    sem_path = MEMORY_DIR / "semantic.json"
    data = load_json(sem_path)
    
    data["facts"] = list(set(data.get("facts", []) + facts))[-50:]
    if preferences:
        data["preferences"] = list(set(data.get("preferences", []) + preferences))[-20:]
    data["last_updated"] = datetime.now().isoformat()
    
    save_json(sem_path, data)

def update_session_state(project: str, path: str, task: str, turns: list):
    """Update session state."""
    state_path = MEMORY_DIR / "session_state.json"
    data = load_json(state_path)
    
    data["project"] = project
    data["project_path"] = path
    data["current_task"] = task
    data["last_3_turns"] = turns[-3:] if turns else []
    data["last_compression"] = datetime.now().isoformat()
    
    save_json(state_path, data)

def compress(conversation: str, project: str = "", path: str = "", task: str = ""):
    """Main compression function."""
    decisions = extract_decisions(conversation)
    facts = extract_facts(conversation)
    
    update_anchor(decisions, project, path)
    update_semantic(facts)
    update_session_state(project, path, task, [])
    
    semantic = load_json(MEMORY_DIR / "semantic.json")
    
    state_block = f"""[ANCHOR] {task} | {', '.join(decisions[:3])}
[SEMANTIC] {'; '.join(facts[:5])}
[PROC] See procedural.md
---RECENT---
(Compressed at {datetime.now().isoformat()})
"""
    return state_block

def get_tiered_context() -> str:
    """Load and format tiered context for prompt injection."""
    anchor = (MEMORY_DIR / "anchor.md").read_text() if (MEMORY_DIR / "anchor.md").exists() else ""
    semantic = load_json(MEMORY_DIR / "semantic.json")
    procedural = (MEMORY_DIR / "procedural.md").read_text() if (MEMORY_DIR / "procedural.md").exists() else ""
    
    sem_str = "; ".join(semantic.get("facts", [])[:10])
    
    return f"""<!-- TIER 0: ANCHOR (from {MEMORY_DIR}) -->
{anchor}

<!-- TIER 1: SEMANTIC -->
Facts: {sem_str}

<!-- TIER 2: PROCEDURAL -->
{procedural}
"""

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "load":
            print(get_tiered_context())
        elif cmd == "compress":
            conv = sys.stdin.read() if not sys.stdin.isatty() else ""
            print(compress(conv))
        elif cmd == "init":
            # Initialize project-local memory
            path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
            mem_dir = init_project_memory(path)
            print(f"Initialized memory at: {mem_dir}")
        elif cmd == "where":
            # Show which memory directory is being used
            print(f"Memory: {MEMORY_DIR}")
    else:
        print("Usage: pulse_compress.py [load|compress|init|where]")
        print(f"Current memory: {MEMORY_DIR}")
