# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Layout

CORTEX is a monorepo composed of two independent components that share a contract via MCP and a single NVIDIA API key:

- `dory/` — TypeScript / Next.js 15 app. The agent runtime, tool implementations, RAG pipeline, vector memory, MCP server, and web UI. This is where almost all code lives.
- `pulse/` — Python launcher / prompt system. Drives an external Codex CLI in `--full-auto` mode through three prompt phases (`prompts/1.md`, `2.md`, `3.md`). PULSE is *deployed* by copying files into `~/.codex/` (see `install.sh`); it is not run from inside this repo.
- `cortex.config.json` — declarative manifest of both components, model IDs, and shared-memory paths. Treat as source of truth for model names.

There is no top-level package manager — each component is installed independently.

## Common Commands

All Node commands run from `dory/`:

```bash
npm install                          # one-time
npm run dev                          # Next.js dev server (localhost:3000)
npm run build                        # production build
npm run lint                         # next lint (ESLint)
npm run lint:sections                # custom CI guard, see "Section linter" below
npm run terminal                     # standalone xterm/pty WebSocket server
npm run dev:all                      # dev + terminal concurrently
npx tsx mcp-server.ts                # run MCP server only (used by Kiro/Codex)
./bin/dory "<message>"               # CLI client that streams from /api/agent-chat
```

There is no test runner configured in either component — do not invent `npm test` or `pytest` commands.

PULSE is exercised post-install via `~/.codex/autoogpt.py -p <project>` and `~/.codex/autoqagpt.py -p <project>`. The `autoogpt.py` / `autoqagpt.py` files in this repo are thin wrappers that hard-code model env vars and shell out to `~/.codex/scripts/autonomous{,_qa}.py` — they only work after `install.sh` has populated `~/.codex/`.

## Section Linter (CI guard)

`dory/scripts/lint-sections.sh` validates `dory/app/api/agent-chat/route.ts`:

1. Every line matching `^[0-9]+\.` must contain a U+2014 em-dash (`—`). Use bullets or letters for sub-steps inside that file.
2. The numbered+em-dash section count must be exactly **29**.

When editing the system prompt in `route.ts`, run `npm run lint:sections` before committing. Adding/removing a top-level section requires updating the expected count in the script.

## DORY Architecture (the part you'll actually touch)

### Request flow
`Web UI → POST /api/agent-chat → agent loop in lib/agents/agent.ts → NVIDIA NIM → tool calls → loop`

The same tool registry is also exposed verbatim through `mcp-server.ts` (stdio MCP) so external CLIs (Kiro, Codex) drive the same code paths as the web UI.

### Agent core
- `lib/agents/agent.ts` — main tool-loop. Tools are looked up by name and invoked with their parsed arguments.
- `lib/agents/tools/registry.ts` — single source of truth for which tools exist. Adding a tool means: implement it in `lib/agents/tools/`, register it here, **and** wire it into `mcp-server.ts` if it should be exposed over MCP.
- `lib/agents/base-tool.ts` — base class all tool classes extend.
- `lib/agents/mcp-agent.ts` + `lib/agents/mcp-agent-runner.ts` — the `dory_agent` meta-tool that runs the full unified-context pipeline as a single tool call from inside another agent.

### Unified context (called before each LLM turn)
- `lib/agents/retrieval-router.ts` decides whether a query needs RAG, web, memory, or none.
- `lib/agents/unified-context.ts` merges RAG hits + vector memory into the prompt.
- `lib/security/pii-guard.ts` redacts emails / phones / API keys / AWS keys / private keys at the API boundary.

### RAG V2 (`lib/agents/rag/`)
Hybrid retrieval following the NVIDIA RAG Blueprint pattern. Pipeline:

`ingest → SwiftTextSplitter (class/struct/func aware) → NV-EmbedQA embeddings → BM25 + vector store`

`query → query-decomposition → hybrid-retriever (BM25+vector, RRF fusion, ~100 candidates) → contextual-retriever (rerank with NV-RerankQA → top 10) → reflection (relevance/groundedness check, may rewrite) → LLM`

Persistence is `.rag-store.json` in the cwd — gitignored. Profiles (iOS / Research / Chatbot) live in `rag/config.ts`. Don't bypass `pipeline-v2.ts` — it owns the full flow including auto-update via `auto-updater.ts`.

### Memory
Two stores, both in `lib/agents/memory/`:
- `vector-memory.ts` → semantic memory persisted to `~/.nvidia-cli/memory/vector-memory.json`. Surfaced via `memory` and `unified_memory` tools.
- Entity memory (people/projects/companies) lives alongside via the `entity_memory` tool.

PULSE has its own memory model (three-tier: `anchor.md` 95%, `semantic.json` 85%, `procedural.md` 60%) at `~/.codex/memory/` — these systems do **not** share a store despite both being called "memory".

### Flywheel (`lib/agents/flywheel/`)
Every interaction is logged (`logger.ts`), optionally LLM-judged (`evaluator.ts`, `trajectory-scorer.ts`), and exportable as SFT/DPO datasets (`dataset-creator.ts`). High-quality traces land in `dory/sft_traces/`, low-quality in `dory/dpo_traces/`. The `flywheel_*` tools expose this to the agent itself.

### NVIDIA model client
`lib/nvidia.ts` is the single client for all four models (LLM / embed / rerank / vision). Hosted endpoint is capped at 262K tokens despite Nemotron's 1M context — self-hosted NIM or Ollama lifts this. Honor the `USE_LOCAL_LLM`, `OLLAMA_BASE_URL`, `LOCAL_EMBED_URL` env vars rather than hardcoding URLs.

## PULSE Pipeline

PULSE is a state machine over `feature_list.json` in the target iOS project:

| Trigger | Prompt | Mode |
|---|---|---|
| no `feature_list.json` or < 150 features | `pulse/prompts/1.md` | Initializer |
| has features, < 100% passing | `pulse/prompts/2.md` | Coder |
| 100% features passing | `pulse/prompts/3.md` | QA |

The launcher writes the chosen prompt to `.codex_prompt.md` in the target project and invokes `codex --full-auto` against it. App is "complete" at 300+ passing features per `pulse/AGENTS.md`.

`pulse/AGENTS.md` is the operating contract for the Codex agent itself (zero hallucination, apply_patch only, Fibonacci spacing, never launch Simulator, etc.). When editing PULSE prompts, conform to those rules — they are enforced behavior, not aspirational.

## Conventions

- **TypeScript paths**: `@/*` aliases the `dory/` root (see `tsconfig.json`). `mcp-server.ts` is excluded from the tsconfig include so it can use `.ts` import specifiers required by `tsx`.
- **ESLint**: warnings only — `@typescript-eslint/no-unused-vars`, `no-explicit-any`, `prefer-const`, `react/no-unescaped-entities` are configured `warn`, not `error`. Don't promote them.
- **Tool registration**: every new tool must appear in both `lib/agents/tools/registry.ts` and `mcp-server.ts` to be reachable from both the web agent and external MCP clients.
- **No tests, no Prisma migrations checked in**: `prisma/dev.db` is referenced in docs but the Prisma schema is not part of the repo. Don't try to run migrations.
- **Hardcoded fallback API key in `mcp-server.ts`**: there is currently a literal `nvapi-...` fallback at the top of the file. If you touch that area, prefer failing fast on missing env over preserving the hardcoded key.

## Environment

Required: `NVIDIA_API_KEY` (or `NGC_API_KEY`, used interchangeably by `lib/nvidia.ts` and `mcp-server.ts`). Single key powers LLM, embeddings, reranker, and vision.

Optional: `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` (web search tools), `CONTEXT7_API_KEY` (Kiro integration), `OPENAI_API_KEY` (PULSE Codex backend), `USE_LOCAL_LLM` / `OLLAMA_BASE_URL` / `LOCAL_EMBED_URL` (local-model mode).

Secrets live in `dory/.env.local` (gitignored) and `~/.codex/config.toml` (gitignored). Never commit either.
