# /compress - PULSE Context Compression

Execute Persistent Unified Learning Session Engine compression.

## MEMORY LOCATION

**Priority order:**
1. `./.codex/memory/` - Project-local (preferred, isolated per project)
2. `~/.codex/memory/` - Global fallback

**Commands:**
```bash
# Check which memory is being used
python3 ~/.codex/scripts/pulse_compress.py where

# Initialize project-local memory (run in project root)
python3 ~/.codex/scripts/pulse_compress.py init

# Load tiered context
python3 ~/.codex/scripts/pulse_compress.py load

# Compress conversation
python3 ~/.codex/scripts/pulse_compress.py compress
```

## COMPRESSION ALGORITHM

### TIER 0: ANCHOR (Never Compress)
Extract and persist to `anchor.md`:
- All "decided to..." / "will use..." / "going with..." statements
- All MUST/NEVER constraints
- Current blockers and impediments
- Project name and path

### TIER 1: SEMANTIC (Extract Facts)
Extract and persist to `semantic.json`:
- Facts: "X is Y", "X uses Y"
- Preferences: "User prefers X", "Always use X"
- Patterns: "When X, do Y"
- Decisions: "Chose X because Y"

### TIER 2: PROCEDURAL (Compress Aggressively)
Summarize to `procedural.md`:
- Code patterns → 1-line summaries
- Build commands → command only
- Resolved debugging → delete entirely

### TIER 3: EPISODIC (Truncate)
Keep only last 3 conversation turns verbatim.
Discard all resolved discussions.

## OUTPUT FORMAT

After compression, output:

```
[ANCHOR] {current_task} | {key_constraints} | {blockers}
[SEMANTIC] {fact1}; {fact2}; {fact3}; ...
[PROC] {1-line procedure summaries}
---RECENT---
{last 3 turns verbatim}
```

## POSITION-AWARE PLACEMENT

After compression, structure context as:
- Position 0-5%: ANCHOR content (highest attention)
- Position 5-15%: SEMANTIC facts
- Position 15-40%: PROCEDURAL (dead zone - expendable)
- Position 85-100%: EPISODIC recent turns (recency boost)

## MULTI-PROJECT ISOLATION

Each project can have its own memory:
```
~/Projects/AppA/.codex/memory/  ← AppA's context
~/Projects/AppB/.codex/memory/  ← AppB's context (isolated)
```

This prevents agents working on different projects from overwriting each other's memory.
