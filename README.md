# CORTEX

CORe + TEX - Unified AI Agent System

DORY (Deep Orchestration and Reasoning sYstem) + PULSE (Persistent Unified Learning Session Engine)

---

## What is CORTEX?

CORTEX is a unified AI agent system that combines two complementary frameworks:

| Component | Full Name | Purpose |
|-----------|-----------|---------|
| DORY | Deep Orchestration and Reasoning sYstem | NVIDIA NIM-powered tool execution, RAG, and memory |
| PULSE | Persistent Unified Learning Session Engine | Autonomous agent orchestration with session memory |

Together, they create a complete AI development assistant with:
- 36 custom tools for file operations, code search, web research, and more
- RAG V2 pipeline with hybrid retrieval (BM25 + Vector) and reranking
- Persistent memory that remembers across sessions
- Autonomous agents that can build entire applications
- MCP integration for universal tool access
- Data flywheel for continuous improvement

---

## Quick Start

### Prerequisites

- Node.js 18+ (for DORY)
- Python 3.11+ (for PULSE)
- NVIDIA API Key from build.nvidia.com
- OpenAI API Key (optional, for PULSE with Codex CLI)

### Installation

```bash
# Clone or download CORTEX
cd /path/to/CORTEX

# DORY Setup
cd dory
npm install
cp .env.example .env.local
# Edit .env.local and add your NVIDIA_API_KEY
npm run dev
# Open http://localhost:3000

# PULSE Setup
cd ../pulse
mkdir -p ~/.codex
cp -r agents prompts memory scripts tools skills rules ~/.codex/
cp autoogpt.py autoqagpt.py ~/.codex/
cp config.toml.example ~/.codex/config.toml
# Edit ~/.codex/config.toml with your settings
```

### Environment Variables

DORY (.env.local):
```env
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_API_KEY=xxx  # Optional - Web search
GOOGLE_CSE_ID=xxx   # Optional - Web search
```

---

## DORY Component

DORY is the NVIDIA-powered AI assistant with:

### NVIDIA Model Stack

| Model | Purpose | Details |
|-------|---------|---------|
| Nemotron 3 Nano | Main LLM | 30B MoE (~3.5B active), 262K context (cloud) / 1M (self-hosted) |
| NV EmbedQA 1B | Embeddings | 2048-dimensional vectors, 8K context per chunk |
| NV RerankQA 1B | Reranking | Re-scores search results, rate limited 1 req/sec |
| Nemotron Nano VL 12B | Vision | 128K context, multi-image reasoning, UI analysis |

### Tools (36)

Project: set_project, get_project
File System: file_read, file_write
System: bash
Reasoning: think
Memory: memory, entity_memory
Search: google_search, parallel_search, local_docs_search
Vision: vision_analyze, ios_ui_review, compare_mockup
RAG: rag_ingest, rag_search, rag_query, rag_research, rag_stats, rag_clear, rag_validate, rag_update
Code: github_analyzer, github_file_reader, code_documentation, documentation_specialist
Diagrams: mermaid_generator, quick_diagram
Specialists: search_specialist, report_planner, section_author, report_writer, quality_reviewer, report_extender, report_compiler, deduplicate_sources

### RAG System

Retrieval-Augmented Generation with:
- Hybrid search (BM25 + Vector)
- NVIDIA reranker for relevance scoring
- Swift-aware chunking
- Query decomposition for complex questions

### Memory System

- Semantic storage with vector embeddings
- Persists across sessions (~/.nvidia-cli/memory/)
- Entity tracking for people, projects, preferences

---

## PULSE Component

PULSE provides autonomous agent orchestration:

### Agents

- AutoOGPT - Autonomous task execution
- AutoQAGPT - Quality assurance and testing
- Custom agents via YAML configuration

### Features

- Session memory persistence
- Multi-agent coordination
- Skill-based task routing
- Integration with Codex CLI

---

## Architecture

```
CORTEX
├── dory/           # NVIDIA-powered AI assistant
│   ├── app/        # Next.js web application
│   ├── lib/        # Core libraries
│   │   ├── agents/ # Agent system and tools
│   │   └── store/  # State management
│   └── components/ # React components
│
└── pulse/          # Autonomous agent system
    ├── agents/     # Agent configurations
    ├── prompts/    # System prompts
    ├── memory/     # Session persistence
    └── tools/      # Python tool implementations
```

---

## MCP Integration

Both DORY and PULSE support Model Context Protocol for universal tool access.

DORY MCP Server (mcp-server.ts):
```toml
[mcp_servers.nvidia-cli]
command = "npx"
args = ["tsx", "/path/to/dory/mcp-server.ts"]
```

---

## Data Flywheel

All interactions are logged locally for:
- Fine-tuning smaller models
- Identifying failure patterns
- Quality measurement over time

Based on NVIDIA's Data Flywheel Blueprint.

---

## License

MIT
