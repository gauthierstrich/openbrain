# Architecture Reference (V2.0 Core)

This document describes the technical architecture of OpenBrain V2.0 — a high-fidelity cognitive operating system. It is intended for contributors, developers building on top of the framework, and users who want to understand how the system works internally.

---

## Table of Contents

- [System Overview](#system-overview)
- [Component Reference](#component-reference)
  - [The Brain Engine](#the-brain-engine-brainpy)
  - [The Telegram Interface](#the-telegram-interface)
  - [The Agent Loader](#the-agent-loader)
  - [The Agent Creator](#the-agent-creator)
  - [The Supervisor](#the-supervisor)
- [Memory Architecture (V2.1 Hybrid Search)](#memory-architecture-v21-hybrid-search)
  - [SQLite FTS5 & Vector Layers](#sqlite-fts5--vector-layers)
  - [Authentication: The OAuth Bridge](#authentication-the-oauth-bridge)
  - [Filesystem Layout](#filesystem-layout)
  - [Memory Flush: Self-Preservation Cycle](#memory-flush-self-preservation-cycle)
  - [High-Fidelity Context Construction](#high-fidelity-context-construction)
  - [Token-Based Compaction](#token-based-compaction)
- [The Intelligence Layer](#the-intelligence-layer)
  - [Native Subprocess Execution (Gemini CLI)](#native-subprocess-execution-gemini-cli)
  - [YOLO Mode](#yolo-mode)
  - [Proactive Learning Cycle](#proactive-learning-cycle)
- [Data Flow Diagrams](#data-flow-diagrams)
- [Security Considerations](#security-considerations)
- [Extension Points](#extension-points)

---

## System Overview

OpenBrain is structured as a **multi-process supervisor** managing one or more **agent processes**. Each agent process handles a single Telegram bot interface backed by a shared `Brain` engine instance. The `Brain` engine orchestrates context construction, LLM invocation, and memory persistence.

The system has no external service dependencies beyond the user's local Gemini CLI installation. Authentication is handled natively through the user's existing OAuth session, eliminating the need for manual API keys.

---

## Component Reference

### The Brain Engine (`brain.py`)

The central orchestration component. Responsible for:

1. **Context construction**: Assembles the full prompt from the agent's soul, user profile, current facts, episodic summary, and recent conversation history.
2. **Memory V2.0 Orchestration**: Reloads recent journals (today/yesterday) and fact file contents into every turn.
3. **LLM invocation**: Calls the Gemini CLI via `subprocess.run()` with the assembled context as stdin.
4. **Memory persistence**: Writes conversation turns to the rolling history file and the daily journal.
5. **Hybrid Search Trigger**: Before every turn, initiates a search in the agent's memory using a weighted score between FTS5 (text) and Gemini Embeddings (semantic).
6. **Flush & Summarization trigger**: When conversation complexity exceeds the token threshold, initiates a silent **Memory Flush** followed by a summarization pass.

**Key design decision**: The brain passes context via `stdin` rather than shell arguments. This prevents prompt injection attacks and avoids shell escaping issues with user-provided content.

### The Telegram Interface (`core/interfaces/telegram.py`)

An `asyncio`-based Telegram bot using `python-telegram-bot`. Each agent runs its own interface instance as a separate OS process.

The interface handles:
- **Access control**: All incoming messages are filtered against the configured `ALLOWED_USER_ID`.
- **Typing simulation**: A background coroutine sends periodic `typing` actions to Telegram during inference, which can take 10–60 seconds depending on context size.
- **Non-blocking dispatch**: LLM calls are dispatched via `loop.run_in_executor()` to avoid blocking the asyncio event loop.

### The Agent Loader (`core/agent_loader.py`)

Scans the `agents/` directory on startup and returns a dictionary of available agents. Each agent is represented by a dataclass containing its `id`, `name`, `emoji`, and filesystem `path`.

### The Agent Creator (`core/agent_creator.py`)

Provisions a new agent directory from a template when the Architect issues a `CREATE_AGENT` instruction. Creates the full directory structure and populates `soul.md`, `user.md`, and `index.md` with the provided content and YOLO mode directives.

### The Supervisor (`scripts/ob-start.py`)

A simple process manager that launches one OS process per configured agent and monitors them for failures. On detection of a `restart.signal` file, the supervisor performs a graceful restart of the affected agent — enabling zero-downtime reconfiguration.

---

## Memory Architecture (V2.1 Hybrid Search)

OpenBrain V2.1 introduces a high-fidelity hybrid search system that achieves parity with advanced cognitive frameworks like OpenClaw.

### SQLite FTS5 & Vector Layers

To provide "instant recall" without high latency, the memory engine (`memory_index.py`) uses two complementary layers:

1. **SQLite FTS5 (Lexical)**: A high-performance full-text search index built into SQLite. It handles keyword matches (e.g. "What was that command for Docker?") using BM25 ranking.
2. **Vector Space (Semantic)**: Text is segmented using an **OpenClaw-parity Double-Pass algorithm**. Chunks are delimited by lines with a budget of **1,000 tokens** (approx. 4,000 chars for Latin, 1,000 chars for CJK). Each chunk is embedded into a 256-dimensional vector using Google's `text-embedding-004` model. Similarity is calculated using cosine similarity in pure Python.

**Scoring Strategy**:
- `Final Score = (FTS Weight * 0.35) + (Vector Weight * 0.65)`

### Authentication: The OAuth Bridge

OpenBrain prioritizes **Zero-Config Security**. Instead of requiring a static `GOOGLE_API_KEY` (which can be leaked or rotated), the system bridges directly into your terminal session:

- **Token Discovery**: The engine automatically reads your Gemini CLI session from `~/.gemini/oauth_creds.json`.
- **Project Mapping**: It identifies your active project from `~/.gemini/projects.json` to ensure correct quota allocation under your personal identity.
- **REST Protocol**: REST API calls for embeddings are authenticated via standard `Authorization: Bearer` headers.

### Filesystem Layout

```
agents/
└── <agent-name>/
    ├── soul.md                          # Agent identity and mission
    ├── user.md                          # User interaction protocol
    ├── index.md                         # Knowledge base table of contents
    └── memory/
        ├── facts/
        │   ├── <topic>.md               # One file per knowledge domain (Indexed by chunks)
        │   └── progress.md              # Cross-agent readable progress file
        ├── journal/
        │   └── YYYY-MM-DD.md            # Daily logs (Indexed and reloaded)
        └── history/
            ├── conversation_history.json  # Rolling window (analyzed for tokens)
            └── history_summary.txt        # LLM-generated episodic summary
```

All files are plain UTF-8 Markdown. No binary formats, no serialization dependencies.

### Memory Flush: Self-Preservation Cycle

In OpenBrain V2.1, the system prevents information loss through a proactive **Flush Cycle**. Before any conversational history is summarized (to save tokens), the engine triggers a silent **Flush Turn**:

1. The history chunk to be summarized is prepared.
2. A silent prompt instructs the agent to identify all **Durable Facts** or **Temporary Journal Notes**.
3. The agent uses its native file-writing tools to save this knowledge into `memory/facts/` or `memory/journal/`.
4. Only after this "Flush" is complete does the engine perform the summarization of the history chunk.

This mirrors the human habit of "taking final notes" before archiving a project.

### High-Fidelity Context Construction

On each inference call, the brain constructs a single text prompt by concatenating the following sections:

| Section | Source | Max Size |
|---------|--------|----------|
| Agent soul | `soul.md` | Unbounded |
| Global user profile | `identity/user.md` | Unbounded |
| Agent user preferences | `user.md` | Unbounded |
| Knowledge base content | **Hybrid Retrieval** | **SQLite FTS5 + Vectors** (V2.1) |
| Recent Journals | **Daily logs** | Indexed & Searchable (V2.1) |
| Episodic summary | `history/history_summary.txt` | Unbounded |
| Recent history | Last 15 turns from JSON | Unbounded |
| Current message | User input | Unbounded |

V2.1 ensures the agent "knows" what happened yesterday and has all its facts directly in mind via a weighted hybrid search, without having to manually search for them.

### Token-Based Compaction

History is no longer compressed based on a fixed message count (legacy limit: 20 turns). Compaction is now triggered by a **Token Budget**:
- **Threshold**: ~8,000 tokens (estimated at 28,000 characters for French).
- **Persistence**: Preservation of the last 15 messages (fixed) ensures the immediate flow isn't broken.

---

## The Intelligence Layer

### Native Subprocess Execution

OpenBrain invokes the Gemini CLI as a subprocess. This provides:
- **Native tool access**: Direct file/directory manipulation via Gemini's built-in tools.
- **Environment inheritance**: Credential persistence and shell tool access.

### YOLO Mode

Invoked with `--yolo`, allowing agents to perform background memory writes (SAVE_FACT) without human approval.

### Proactive Learning Cycle

In V2.0, this cycle is dual-tracked:
1. **Interactive Learning**: Real-time memory updates during conversation via `SAVE_FACT`.
2. **Archival Learning (Flush)**: Systematic knowledge extraction before historical compaction.

---

## Data Flow Diagrams

### Message Processing (V2.0)

```
User message (Telegram)
        │
        ▼
[Access control check]
        │
        ▼
[Volume/Token check] ─► [Trigger FLUSH + SUMMARIZE if >8000 tokens]
        │                   │
        │                   └─► 1. Ask Gemini to SAVE_FACTS silently
        │                   └─► 2. Summarize oldest turns
        ▼
[Build context prompt]
  soul + user + FULL_FACTS + RECENT_JOURNALS + summary + history + message
        │
        ▼
[gemini -y -m gemini-3.0-flash-preview] ◄── stdin: context prompt
        │
        ▼
[Parse response]
        │
        ▼
[Append history JSON] + [Write journal log]
        │
        ▼
[Send response to user]
```

---

## Security Considerations

| Surface | Risk | Mitigation |
|---------|------|------------|
| Telegram access | Unauthorized users | Hard `ALLOWED_USER_ID` check on every message |
| YOLO mode file access | Agent writes outside memory/ | Instructional confinement; OS-level user permissions |
| `.env` token exposure | Token leak if committed to Git | `.env` is in `.gitignore` |

---

## Extension Points

- **New interfaces**: CLI, Discord, etc. by reusing the `Brain` engine.
- **Alternative LLM backends**: The context construction is backend-agnostic (designed for high-fidelity text prompts).
- **Custom sensors**: The `core/sensors/` directory can host background jobs that feed data into the agent's journals.

---
*OpenBrain Core V2.0 — Engineering for Autonomy and Intelligence.*
