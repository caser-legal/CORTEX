# PULSE

Persistent Unified Learning Session Engine

Autonomous iOS Development System powered by Codex CLI

---

## Quick Start

```bash
# Single app - Build
autoogpt -p /Users/home/Documents/iOS/AppName

# Single app - QA
autoqagpt -p /Users/home/Documents/iOS/AppName

# Monitor all running agents
~/.codex/scripts/monitor.sh

# Build all in-progress apps
~/.codex/scripts/run_autoogpt_inprogress.sh
```

---

## Directory Structure

```
~/.codex/
├── Launchers
│   ├── autoogpt.py              # Codex coding launcher
│   └── autoqagpt.py             # Codex QA launcher
│
├── agents/
│   ├── agent.py                 # Main autonomous loop
│   ├── agent_qa.py              # QA agent loop
│   ├── qa_checklist.py          # QA verification
│   ├── progress.py              # Progress tracking
│   └── prompts.py               # Prompt management
│
├── prompts/
│   ├── 1.md                     # Initializer prompt
│   ├── 2.md                     # Coding prompt
│   ├── 3.md                     # QA prompt
│   ├── initializer_prompt.md    # Feature generation
│   ├── coding_prompt.md         # Implementation
│   └── qa_prompt.md             # QA verification
│
├── memory/                      # PULSE memory system
│   ├── anchor.md                # Tier 0 (95% attention)
│   ├── semantic.json            # Tier 1 (85% attention)
│   └── procedural.md            # Tier 2 (60% attention)
│
└── scripts/
    ├── memory_sync.py           # Memory sync
    ├── ui_preflight.py          # UI checker
    └── monitor.sh               # Dashboard
```

---

## System Architecture

```
Launch Layer
├── autoogpt.py
└── autoqagpt.py
        │
        v
Agent Layer
├── agent.py
└── agent_qa.py
        │
        v
Codex CLI
├── codex --full-auto
└── .codex_prompt.md
        │
        v
Memory System
├── anchor.md (Tier 0)
├── semantic.json (Tier 1)
└── procedural.md (Tier 2)
```

---

## Agent System

### AutoOGPT (Coding Agent)

Autonomous app builder that:
1. Reads feature list from progress.json
2. Implements features one by one
3. Runs xcodebuild to verify compilation
4. Updates progress tracking
5. Continues until all features complete

### AutoQAGPT (QA Agent)

Quality assurance agent that:
1. Reviews implemented features
2. Runs UI preflight checks
3. Verifies SwiftUI best practices
4. Reports issues and suggestions

---

## Memory System

Three-tier memory architecture:

| Tier | File | Attention | Purpose |
|------|------|-----------|---------|
| 0 | anchor.md | 95% | Critical context, current task |
| 1 | semantic.json | 85% | Project knowledge, patterns |
| 2 | procedural.md | 60% | General procedures, templates |

Memory persists across sessions and syncs automatically.

---

## Features

- Autonomous iOS app development
- SwiftUI/iOS 18 best practices
- Automatic compilation verification
- Progress tracking and resumption
- Multi-agent coordination
- Session memory persistence

---

## Integration with DORY

PULSE can use DORY's tools via MCP:

```toml
[mcp_servers.nvidia-cli]
command = "npx"
args = ["tsx", "/path/to/dory/mcp-server.ts"]
```

This gives PULSE access to:
- RAG search over codebases
- Persistent vector memory
- Vision analysis for UI review
- Web search capabilities

---

## Requirements

- Python 3.11+
- Codex CLI (npm install -g @openai/codex)
- Xcode 16+ (for iOS development)
- OpenAI API key

---

## License

MIT
