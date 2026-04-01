# Architecture Reference

This document describes the technical architecture of OpenBrain. It is intended for contributors, developers building on top of the framework, and users who want to understand how the system works internally.

---

## Table of Contents

- [System Overview](#system-overview)
- [Component Reference](#component-reference)
  - [The Brain Engine](#the-brain-engine-brainpy)
  - [The Telegram Interface](#the-telegram-interface)
  - [The Agent Loader](#the-agent-loader)
  - [The Agent Creator](#the-agent-creator)
  - [The Supervisor](#the-supervisor)
- [Memory Architecture](#memory-architecture)
  - [Filesystem Layout](#filesystem-layout)
  - [Context Window Construction](#context-window-construction)
  - [Episodic Summarization](#episodic-summarization)
- [The Intelligence Layer](#the-intelligence-layer)
  - [Native Subprocess Execution](#native-subprocess-execution)
  - [YOLO Mode](#yolo-mode)
  - [Proactive Learning Cycle](#proactive-learning-cycle)
- [Data Flow Diagrams](#data-flow-diagrams)
- [Security Considerations](#security-considerations)
- [Extension Points](#extension-points)

---

## System Overview

OpenBrain is structured as a **multi-process supervisor** managing one or more **agent processes**. Each agent process handles a single Telegram bot interface backed by a shared `Brain` engine instance. The `Brain` engine orchestrates context construction, LLM invocation, and memory persistence.

The system has no external service dependencies beyond the user's local Gemini CLI installation. There is no database, no vector store, and no background sync process.

---

## Component Reference

### The Brain Engine (`brain.py`)

The central orchestration component. Responsible for:

1. **Context construction**: Assembles the full prompt from the agent's soul, user profile, current facts, episodic summary, and recent conversation history.
2. **LLM invocation**: Calls the Gemini CLI via `subprocess.run()` with the assembled context as stdin.
3. **Memory persistence**: Writes conversation turns to the rolling history file and the daily journal.
4. **Summarization trigger**: When conversation history exceeds the configured threshold, initiates an episodic summarization pass.

**Key design decision**: The brain passes context via `stdin` rather than shell arguments. This prevents prompt injection attacks and avoids shell escaping issues with user-provided content.

### The Telegram Interface (`core/interfaces/telegram.py`)

An `asyncio`-based Telegram bot using `python-telegram-bot`. Each agent runs its own interface instance as a separate OS process.

The interface handles:
- **Access control**: All incoming messages are filtered against the configured `ALLOWED_USER_ID`.
- **Typing simulation**: A background coroutine sends periodic `typing` actions to Telegram during inference, which can take 10–60 seconds depending on context size.
- **Non-blocking dispatch**: LLM calls are dispatched via `loop.run_in_executor()` to avoid blocking the asyncio event loop.

### The Agent Loader (`core/agent_loader.py`)

Scans the `agents/` directory on startup and returns a dictionary of available agents. Each agent is represented by a dataclass containing its `id`, `name`, `emoji`, and filesystem `path`.

The loader performs automatic structure validation, creating any missing directories (`memory/facts/`, `memory/journal/`, `memory/history/`) to ensure agents are always in a consistent state.

### The Agent Creator (`core/agent_creator.py`)

Provisions a new agent directory from a template when the Architect issues a `CREATE_AGENT` instruction. Creates the full directory structure and populates `soul.md`, `user.md`, and `index.md` with the provided content and YOLO mode directives.

### The Supervisor (`scripts/ob-start.py`)

A simple process manager that launches one OS process per configured agent and monitors them for failures. On detection of a `restart.signal` file, the supervisor performs a graceful restart of the affected agent — enabling zero-downtime reconfiguration.

---

## Memory Architecture

### Filesystem Layout

```
agents/
└── <agent-name>/
    ├── soul.md                          # Agent identity and mission
    ├── user.md                          # User interaction protocol
    ├── index.md                         # Knowledge base table of contents
    └── memory/
        ├── facts/
        │   ├── <topic>.md               # One file per knowledge domain
        │   └── progress.md              # Cross-agent readable progress file
        ├── journal/
        │   └── YYYY-MM-DD.md            # Daily conversation logs
        └── history/
            ├── conversation_history.json  # Rolling window (last 50 turns)
            └── history_summary.txt        # LLM-generated episodic summary
```

All files are plain UTF-8 Markdown. No binary formats, no serialization dependencies.

### Context Window Construction

On each inference call, the brain constructs a single text prompt by concatenating the following sections in order:

| Section | Source | Max Size |
|---------|--------|----------|
| Agent soul | `soul.md` | Unbounded |
| Global user profile | `identity/user.md` | Unbounded |
| Agent user preferences | `user.md` | Unbounded |
| Knowledge index | `index.md` | Unbounded |
| Fact documents | All `memory/facts/*.md` | 1,500 chars per file (truncated) |
| Episodic summary | `history/history_summary.txt` | Unbounded |
| Recent history | Last 15 turns from JSON | Unbounded |
| Current message | User input | Unbounded |

Individual fact files are truncated at 1,500 characters to prevent context overflow on agents with large knowledge bases. Future versions will implement semantic retrieval to handle arbitrarily large fact stores.

### Episodic Summarization

When the conversation history file exceeds 20 turns, the brain initiates a summarization pass:

1. The oldest 5+ turns are extracted from the history file.
2. A summarization prompt is constructed, combining the existing episodic summary with the turns to be compressed.
3. The summarization prompt is sent to Gemini (a separate subprocess call).
4. The result is written to `history_summary.txt`, replacing the previous summary.
5. The compressed turns are removed from `conversation_history.json`.

This maintains O(1) context growth regardless of conversation length.

---

## The Intelligence Layer

### Native Subprocess Execution

OpenBrain invokes the Gemini CLI as a subprocess rather than using the Gemini API directly. This architectural choice provides several significant advantages:

- **Native tool access**: Gemini CLI in YOLO mode has built-in tools for file system operations, shell execution, and web browsing. These tools are available to the agent without any additional implementation.
- **Environment inheritance**: The subprocess inherits the full shell environment, including any authenticated credentials, PATH configurations, and system resources.
- **No API key management in code**: Authentication is handled entirely by the Gemini CLI's credential store.

The tradeoff is process startup latency (~200–500ms per call for Node.js initialization). For interactive conversation use cases, this overhead is acceptable.

### YOLO Mode

The Gemini CLI is invoked with the `-y` (`--yolo`) flag, which automatically approves all tool call confirmations. This is required for agents to write files to disk autonomously.

**Security note**: YOLO mode grants the agent the ability to execute shell commands and modify files with the permissions of the running process. OpenBrain mitigates this by running each agent as a non-privileged user process. Users should be aware of this capability and treat agent soul files as trusted code.

### Proactive Learning Cycle

Agents are designed to autonomously detect and persist new information during normal conversation. The mechanism is entirely prompt-based — the agent's `soul.md` instructs it to write new facts to `memory/facts/` using native CLI tools whenever it encounters information it doesn't already have.

This cycle follows a Perceive → Reason → Write pattern:

1. **Perceive**: Agent receives a message containing new information (a date, a preference, a biographical fact).
2. **Reason**: Agent determines whether this information is novel relative to its current knowledge base (by checking its loaded facts in context).
3. **Write**: Agent uses native file-writing tools to create or update the appropriate `memory/facts/<topic>.md` file and updates `index.md` to reference it.

No custom tooling is required. This is a behavioral property of the agent, not a framework feature.

---

## Data Flow Diagrams

### Message Processing

```
User message (Telegram)
        │
        ▼
[Access control check]
        │
        ▼
[Load conversation history] ──► [Trigger summarization if >20 turns]
        │
        ▼
[Build context prompt]
  soul + user + index + facts + summary + history + message
        │
        ▼
[gemini -y -m <model>] ◄── stdin: context prompt
        │
        ▼
[Parse response]
        │
        ▼
[Append to history JSON] + [Write to daily journal]
        │
        ▼
[Send response to user]
```

---

## Security Considerations

| Surface | Risk | Mitigation |
|---------|------|------------|
| Telegram access | Unauthorized users | Hard `ALLOWED_USER_ID` check on every message |
| Prompt injection via user input | Malicious content in soul/facts | Context is passed via stdin, not shell args |
| YOLO mode file access | Agent writes outside memory/ | Agent is instructed to write only to its memory directory; no enforcement at OS level |
| `.env` token exposure | Token leak if committed to Git | `.env` is in `.gitignore`; `.env.example` provided as reference |
| Agent cross-access | One agent reading another's private memory | Currently no enforcement; agents have read access to the full storage path |

---

## Extension Points

OpenBrain is designed to be extended at several layers:

- **New interfaces**: Implement a new interface alongside `core/interfaces/telegram.py` (e.g., web, CLI, Discord) by reusing the `Brain` engine directly.
- **New agent templates**: Add agent templates to the `template/agents/` directory. The Architect automatically discovers and can instantiate them.
- **Alternative LLM backends**: Replace the `ask_gemini()` method in `brain.py` to use a different CLI or API. The context construction logic is backend-agnostic.
- **Custom system actions**: The `handle_system_actions()` method in `brain.py` can be extended with new action types that map to Python-side operations.
