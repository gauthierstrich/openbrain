# OpenBrain

> A local-first, modular multi-agent framework that transforms your personal knowledge into an autonomous, evolving intelligence — hosted entirely on your own machine.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Gemini%20CLI-4285F4)](https://github.com/google-gemini/gemini-cli)
[![Status: v2.1](https://img.shields.io/badge/Status-v2.1%20Stable-green)]()

---

## Overview

OpenBrain is an open-source **multi-agent cognitive framework** built around a fundamental principle: your intelligence should live on your machine, not in a corporate cloud.

Unlike SaaS-based AI assistants that reset between sessions, OpenBrain agents maintain **persistent, structured memory** across every conversation. Over time, each agent builds a rich semantic knowledge base about its user — autonomously, silently, and without requiring any manual curation.

The system is designed around **three core properties**:

- **Local-First**: All data — facts, conversations, identity — is stored as plain Markdown files on your filesystem. No third-party databases. No telemetry.
- **Modular by Design**: Each agent is a self-contained unit with its own identity (`soul.md`), user interaction protocol (`user.md`), and semantic memory (`memory/`).
- **Natively Intelligent**: Agents run on top of Gemini CLI with full system access. They can read files, explore directories, and write knowledge to disk — without middleware, without tool-calling abstractions.

---

## Table of Contents

- [Architecture](#architecture)
- [The Agent Model](#the-agent-model)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Multi-Agent Ecosystem](#multi-agent-ecosystem)
- [Memory System](#memory-system)
- [Configuration Reference](#configuration-reference)
- [Contributing](#contributing)

---

## Architecture

OpenBrain follows a **memory-centric, event-driven** architecture. The system is designed to be stateless at the process level and stateful at the filesystem level — ensuring resilience, transparency, and zero data loss on crash.

```
┌─────────────────────────────────────────────────────────────┐
│                     User (Telegram)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               Telegram Interface (asyncio)                  │
│  - Handles polling, typing indicators, access control       │
│  - Dispatches messages to Brain via run_in_executor()       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Brain Engine                             │
│  - Builds full context: soul + user + memory + history      │
│  - Invokes gemini-cli subprocess with --yolo flag           │
│  - Handles proactive episodic summarization (>20 turns)     │
│  - Dispatches system actions to disk                        │
└─────────────────────────────────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
┌─────────────────────┐  ┌─────────────────────────────────┐
│    Gemini CLI       │  │    Filesystem (Agent Memory)    │
│  (subprocess.run)   │  │                                 │
│  - Full YOLO mode   │  │  agents/<name>/                 │
│  - Native file      │  │  ├── soul.md                    │
│    access tools     │  │  ├── user.md                    │
│  - Internet access  │  │  ├── index.md                   │
└─────────────────────┘  │  └── memory/                    │
                         │      ├── facts/                  │
                         │      ├── journal/                │
                         │      └── history/                │
                         └─────────────────────────────────┘
```

For a complete technical deep-dive, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## The Agent Model

Every OpenBrain agent is composed of **three atomic primitives**:

### `soul.md` — Identity & Mission
The foundational document that defines what the agent *is*. It contains its purpose, its behavioral constraints, its communication style, and its proactive learning directives. The soul is loaded at the start of every inference call and forms the immutable identity layer of the agent.

### `user.md` — Interaction Protocol  
A human-authored document that specifies how the user wants to be addressed, their preferences, their background context, and any specific rules the agent must follow. This separates *who the agent is* from *how it should behave with this specific person*.

### `memory/` — Semantic Knowledge Base
A hierarchical, plain-text store that evolves throughout the lifetime of the agent:

| Path | Purpose |
|------|---------|
| `memory/facts/*.md` | Structured factual knowledge about the user, organized by topic |
| `memory/journal/YYYY-MM-DD.md` | Timestamped record of every conversation |
| `memory/history/conversation_history.json` | Rolling window of recent turns (last 50) |
| `memory/history/history_summary.txt` | LLM-generated episodic summary of older conversations |
| `index.md` | Human-readable table of contents linking all facts |

---

## Installation

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | Standard library only for core engine |
| [gemini-cli](https://github.com/google-gemini/gemini-cli) | Latest | Must be authenticated (`gemini login`) |
| Telegram Bot Token | — | One token per agent, obtained via [@BotFather](https://t.me/BotFather) |
| Telegram User ID | — | Your personal Telegram ID (e.g., from [@userinfobot](https://t.me/userinfobot)) |

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/gauthierstrich/openbrain.git
cd openbrain

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure your environment
cp .env.example .env
# Edit .env with your Telegram tokens and user ID

# 4. Launch the supervisor
python3 scripts/ob-start.py
```

---

## Quickstart

Once the supervisor is running, the **Architect** — your system configuration agent — is available on Telegram.

The Architect guides you through the creation of your first personal agent in a fully conversational flow. No YAML editing, no config files, no technical knowledge required. You describe what you need; the Architect provisions the infrastructure.

**Typical onboarding flow:**
1. `/start` → Architect introduces the system
2. Describe the agent you want (e.g., "a personal assistant who knows my life")
3. Architect asks clarifying questions to define the agent's soul and interaction style
4. Architect instructs you to create a bot via @BotFather and provide the token
5. The agent is deployed and immediately available

---

## Multi-Agent Ecosystem

OpenBrain is designed for **parallel agent deployment**. The supervisor (`ob-start.py`) manages the full lifecycle of every agent — launching, monitoring, and restarting them as needed.

A standard ecosystem includes:

| Agent | Role |
|-------|------|
| **Architect** | System configuration, agent creation, infrastructure management |
| **Personal Assistant** | Long-term memory of the user's life, goals, and agenda |
| **Domain Specialists** | Focused agents for specific subjects (e.g., Finance, Academic subjects) |

Cross-agent awareness is built-in: the Personal Assistant has read access to the `progress.md` file of each specialist, enabling holistic planning across all active agents.

---

## Memory System

OpenBrain's memory system is designed for **longevity and human readability**.

### Proactive Fact Ingestion
Agents are instructed to autonomously detect new information about the user and write it to `memory/facts/` using the native file-writing capabilities of Gemini CLI. This happens silently, in the background, during normal conversation — mimicking the way a human expert takes notes.

### Episodic Summarization
Conversation history is preserved in two layers:
- **Short-term**: The last 50 turns in JSON format, injected verbatim into the model's context window.
- **Long-term**: When the history exceeds 20 turns, the engine triggers a summarization pass. The resulting summary is stored and re-injected as compressed episodic memory, ensuring no information is ever fully discarded.

### The Index
Each agent maintains a `index.md` — a markdown table of contents that maps every known topic to its corresponding fact file. The agent updates this index proactively as its knowledge base grows.

---

## Configuration Reference

All runtime configuration is managed via a single `.env` file at the project root.

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_MODEL` | Yes | Model identifier (e.g., `gemini-2.0-flash`) |
| `BRAIN_STORAGE_PATH` | Yes | Absolute path to the directory containing the `agents/` folder |
| `ALLOWED_USER_ID` | Yes | Telegram user ID of the authorized user |
| `USER_LANGUAGE` | No | Response language code (default: `fr`) |
| `TELEGRAM_TOKEN_<AGENT>` | Yes (per agent) | Bot token for each agent (e.g., `TELEGRAM_TOKEN_PERSONAL`) |

See [`.env.example`](.env.example) for a complete reference.

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

This project follows a strict separation between:
- **Core engine changes** (require architectural discussion)
- **Template improvements** (open for direct PRs)
- **Documentation** (always welcome)

---

## License

MIT License. See [LICENSE](LICENSE) for details.
