<p align="center">
  <img src="dory/public/nvidia-logo.webp" alt="CORTEX" width="120" />
</p>

<h1 align="center"> CORTEX</h1>

<p align="center">
  <strong>CORe + TEX — Unified AI Agent System</strong><br/>
  <em>DORY (Deep Orchestration & Reasoning sYstem) + PULSE (Persistent Unified Learning Session Engine)</em>
</p>

<p align="center">
  <a href="#-what-is-cortex">What is CORTEX?</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-dory-component">DORY</a> •
  <a href="#-pulse-component">PULSE</a> •
  <a href="#-integration">Integration</a> •
  <a href="#-architecture">Architecture</a>
</p>

---

#  What is CORTEX?

**CORTEX** is a unified AI agent system that combines two complementary frameworks:

| Component | Full Name | Purpose |
|-----------|-----------|---------|
| [**DORY**](https://github.com/caser-legal/nvidia-cli) | Deep Orchestration & Reasoning sYstem | NVIDIA NIM-powered tool execution, RAG, and memory |
| [**PULSE**](https://github.com/caser-legal/CORTEX/tree/main/pulse) | Persistent Unified Learning Session Engine | Autonomous agent orchestration with session memory |

Together, they create a complete AI development assistant with:
- **36 custom tools** for file operations, code search, web research, and more
- **RAG V2 pipeline** with hybrid retrieval (BM25 + Vector) and reranking
- **Persistent memory** that remembers across sessions
- **Autonomous agents** that can build entire applications
- **MCP integration** for universal tool access
- **Data flywheel** for continuous improvement

---

#  Quick Start

## Prerequisites

- **Node.js** 18+ (for DORY)
- **Python** 3.11+ (for PULSE)
- **NVIDIA API Key** from [build.nvidia.com](https://build.nvidia.com)
- **OpenAI API Key** (optional, for PULSE with Codex CLI)

## Installation

```bash
# Clone or download CORTEX
cd /path/to/CORTEX

# === DORY Setup ===
cd dory
npm install

# Create environment file
cp .env.example .env.local
# Edit .env.local and add your NVIDIA_API_KEY

# Start DORY web interface
npm run dev
# Open http://localhost:3000

# === PULSE Setup ===
cd ../pulse

# Copy to ~/.codex (PULSE home directory)
mkdir -p ~/.codex
cp -r agents prompts memory scripts tools skills rules ~/.codex/
cp autoogpt.py autoqagpt.py ~/.codex/
cp config.toml.example ~/.codex/config.toml
# Edit ~/.codex/config.toml with your settings

# Install Codex CLI (if using PULSE)
npm install -g @openai/codex
```

## Environment Variables

### DORY (.env.local)

```env
# Required - Single key for all NVIDIA services
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional - Web search
GOOGLE_API_KEY=xxx
GOOGLE_CSE_ID=xxx

# Optional - Local LLM
USE_LOCAL_LLM=true
OLLAMA_BASE_URL=http://localhost:11434

# Optional - Logging
LOG_LEVEL=info
LOG_JSON=true
```

### PULSE (~/.codex/config.toml)

```toml
model = "o4-mini"
model_provider = "openai"

# Connect PULSE to DORY's MCP server
[mcp_servers.dory]
command = "npx"
args = ["tsx", "/path/to/CORTEX/dory/mcp-server.ts"]
cwd = "/path/to/CORTEX/dory"
startup_timeout_sec = 120
tool_timeout_sec = 120
env = { NVIDIA_API_KEY = "${NVIDIA_API_KEY}" }
```

---

#  DORY Component

**Location:** `./dory/`

DORY is the NVIDIA NIM-powered backend providing tools, RAG, and memory.

## Features

| Feature | Description |
|---------|-------------|
| **35 Custom Tools** | File ops, bash, RAG, search, memory, vision, diagrams |
| **RAG V2 Pipeline** | Hybrid BM25+Vector retrieval with NVIDIA reranker |
| **Vector Memory** | Semantic memory that persists across sessions |
| **MCP Server** | Exposes all tools via Model Context Protocol |
| **Data Flywheel** | Logs interactions for future model fine-tuning |
| **Web Interface** | Next.js chat UI at localhost:3000 |

## NVIDIA Model Stack

All models accessed with a single `NVIDIA_API_KEY`:

| Model | Purpose |
|-------|---------|
| **Nemotron 3 Nano 30B** | Main LLM (1M context, MoE architecture) |
| **NV-EmbedQA 1B v2** | Embeddings (2048-dim vectors) |
| **NV-RerankQA 1B v2** | Reranking search results |
| **Nemotron Nano VL 12B v2** | Vision analysis |

## Tool Categories

| Category | Tools |
|----------|-------|
| **File System** | `file_read`, `file_write`, `bash`, `set_project`, `get_project` |
| **RAG** | `rag_ingest`, `rag_search`, `rag_query`, `rag_research`, `rag_stats`, `rag_clear`, `rag_validate`, `rag_update` |
| **Search** | `google_search`, `parallel_search`, `local_docs_search` |
| **Memory** | `memory`, `entity_memory` |
| **Vision** | `vision_analyze`, `ios_ui_review`, `compare_mockup` |
| **Code** | `github_analyzer`, `github_file_reader`, `code_documentation` |
| **Diagrams** | `mermaid_generator`, `quick_diagram` |
| **Specialists** | `search_specialist`, `report_planner`, `section_author`, `report_writer`, `quality_reviewer` |

## Running DORY

```bash
cd dory

# Development mode
npm run dev

# MCP server only (for external clients)
npx tsx mcp-server.ts
```

---

#  PULSE Component

**Location:** `./pulse/`

PULSE is the autonomous agent orchestration system with session memory.

## Features

| Feature | Description |
|---------|-------------|
| **Autonomous Agents** | Build entire apps with minimal intervention |
| **Tiered Memory** | Anchor (95%), Semantic (85%), Procedural (60%) attention |
| **Multi-Agent Modes** | Initializer, Coder, QA agents |
| **Session Persistence** | Remembers context across sessions |
| **Progress Tracking** | Visual progress from 0% to 100% |

## Agent Modes

| Mode | Prompt | Trigger |
|------|--------|---------|
| **Initializer** | `@1` → `1.md` | No feature_list.json or < 150 features |
| **Coder** | `@2` → `2.md` | Has features, not 100% passing |
| **QA** | `@3` → `3.md` | 100% features passing |

## Memory Tiers

| Tier | File | Attention | Contents |
|:----:|------|:---------:|----------|
| 🔴 **0** | `anchor.md` | **95%** | MUST/NEVER rules, project state |
| 🟠 **1** | `semantic.json` | **85%** | Facts, patterns, preferences |
| 🟡 **2** | `procedural.md` | **60%** | Code patterns, commands |

## Running PULSE

```bash
# Single app - Build
~/.codex/autoogpt.py -p /path/to/project

# Single app - QA
~/.codex/autoqagpt.py -p /path/to/project

# Monitor all running agents
~/.codex/scripts/monitor.sh

# Build all in-progress apps
~/.codex/scripts/run_autoogpt_inprogress.sh
```

---

# 🔗 Integration

CORTEX integrates DORY and PULSE via MCP (Model Context Protocol).

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                        CORTEX                               │
├─────────────────────────┬───────────────────────────────────┤
│         DORY            │           PULSE                   │
│  ┌─────────────────┐    │    ┌─────────────────┐            │
│  │  NVIDIA NIM     │    │    │  Anchor Memory  │            │
│  │  (LLM Backend)  │    │    │  (Session State)│            │
│  └────────┬────────┘    │    └────────┬────────┘            │
│           │             │             │                     │
│  ┌────────▼────────┐    │    ┌────────▼────────┐            │
│  │   RAG V2        │◄───┼────│  Agent System   │            │
│  │   Pipeline      │    │    │  (Multi-Agent)  │            │
│  └────────┬────────┘    │    └────────┬────────┘            │
│           │             │             │                     │
│  ┌────────▼────────┐    │    ┌────────▼────────┐            │
│  │   MCP Server    │◄───┼────│  Codex CLI      │            │
│  │   (35 Tools)    │    │    │  (Orchestrator) │            │
│  └─────────────────┘    │    └─────────────────┘            │
└─────────────────────────┴───────────────────────────────────┘
```

## MCP Connection

PULSE agents connect to DORY's MCP server to access all 36 tools:

```toml
# ~/.codex/config.toml
[mcp_servers.dory]
command = "npx"
args = ["tsx", "/path/to/CORTEX/dory/mcp-server.ts"]
cwd = "/path/to/CORTEX/dory"
startup_timeout_sec = 120
tool_timeout_sec = 120
env = { NVIDIA_API_KEY = "${NVIDIA_API_KEY}" }
```

This gives PULSE agents access to:
- NVIDIA-powered RAG search
- Vector memory storage
- File operations with PII protection
- Web search capabilities
- Vision analysis

---

#  Architecture

## Complete System Flow

```mermaid
flowchart TB
    subgraph User["👤 User"]
        WEB[Web Interface<br/>localhost:3000]
        CLI[Codex CLI<br/>Terminal]
    end

    subgraph DORY[" DORY"]
        API[Next.js API<br/>Agent Endpoint]
        AGENT[Agent Core<br/>Tool Loop]
        RAG[RAG V2<br/>Hybrid Search]
        MEM[Vector Memory<br/>Semantic Store]
        MCP[MCP Server<br/>35 Tools]
        FLY[Flywheel<br/>Data Logging]
    end

    subgraph PULSE[" PULSE"]
        LAUNCH[Launchers<br/>autoogpt/autoqagpt]
        AGENTS[Agent System<br/>Init/Code/QA]
        ANCHOR[Anchor Memory<br/>Session State]
        SCRIPTS[Scripts<br/>Automation]
    end

    subgraph NVIDIA["☁️ NVIDIA NIM"]
        LLM[Nemotron 3 Nano<br/>1M Context]
        EMB[NV-EmbedQA<br/>Embeddings]
        RR[NV-RerankQA<br/>Reranking]
    end

    WEB --> API --> AGENT
    CLI --> LAUNCH --> AGENTS
    
    AGENT --> RAG --> EMB
    AGENT --> MEM --> EMB
    AGENT --> MCP
    AGENT --> FLY
    RAG --> RR
    AGENT --> LLM
    
    AGENTS --> MCP
    AGENTS --> ANCHOR
    AGENTS --> SCRIPTS

    style DORY fill:#76b900
    style PULSE fill:#0984e3
    style NVIDIA fill:#1a1a2e
```

## Directory Structure

```
CORTEX/
├── README.md                    # This file
│
├── dory/                        # NVIDIA NIM Backend
│   ├── app/                     # Next.js pages & API routes
│   │   ├── api/agent-chat/      # Main agent endpoint
│   │   └── settings/            # Settings page
│   ├── lib/
│   │   ├── agents/              # Agent core, tools, RAG, memory
│   │   │   ├── tools/           # 35 tool implementations
│   │   │   ├── rag/             # RAG V2 pipeline
│   │   │   ├── memory/          # Vector memory store
│   │   │   └── flywheel/        # Data logging
│   │   └── security/            # PII guard
│   ├── components/              # React UI components
│   ├── mcp-server.ts            # MCP server entry point
│   └── package.json
│
└── pulse/                       # Autonomous Agent System
    ├── agents/                  # Agent implementations
    │   ├── agent.py             # Main autonomous loop
    │   ├── agent_qa.py          # QA agent
    │   └── prompts/             # Agent prompts
    ├── prompts/                 # System prompts (1.md, 2.md, 3.md)
    ├── memory/                  # Memory templates
    │   ├── anchor.md            # Tier 0 memory
    │   └── procedural.md        # Tier 2 memory
    ├── scripts/                 # Automation scripts
    ├── tools/                   # Python tools
    ├── autoogpt.py              # Build launcher
    └── autoqagpt.py             # QA launcher
```

---

#  Key Metrics

| Metric | Value |
|--------|-------|
| **Tools** | 35 custom implementations |
| **Context Window** | 1,000,000 tokens (Nemotron 3 Nano) |
| **Embedding Dimensions** | 2,048 (NV-EmbedQA) |
| **RAG Chunk Size** | 800 characters |
| **Quality Threshold** | 7/10 (for training data) |
| **Memory Tiers** | 3 (Anchor, Semantic, Procedural) |
| **Agent Modes** | 3 (Initializer, Coder, QA) |

---

#  Security

## PII Guard (DORY)

Automatically redacts sensitive data:

| Pattern | Replacement |
|---------|-------------|
| Email addresses | `[EMAIL_REDACTED]` |
| Phone numbers | `[PHONE_REDACTED]` |
| API keys | `[API_KEY_REDACTED]` |
| AWS keys | `[AWS_KEY_REDACTED]` |
| Private keys | `[PRIVATE_KEY_REDACTED]` |

## Best Practices

- Never commit `.env.local` or `config.toml` with real keys
- Use environment variables for all secrets
- Keep `~/.nvidia-cli/memory/` backed up but private

---

#  Additional Documentation

- **DORY Details:** See `dory/README.md` for complete tool documentation
- **PULSE Details:** See `pulse/README.md` for agent system documentation
- **AGENTS.md:** See `pulse/AGENTS.md` for agent configuration

---

# 🔮 Roadmap

- [ ] Fine-tune smaller models on flywheel data
- [ ] Add more specialist agents
- [ ] Improve RAG chunking for Swift/iOS
- [ ] Mobile app for remote access
- [ ] Voice input integration

---

<p align="center">
  <sub>Built with  CORTEX = DORY + PULSE</sub><br/>
  <sub>Powered by NVIDIA NIM • OpenAI Codex • ❤️</sub>
</p>
