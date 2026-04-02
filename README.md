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
- **Natively Intelligent (V2.1)**: Agents run on top of Gemini CLI with full system access. They feature **Hybrid Semantic Memory** (BM25 + Cosine Similarity) and full **OAuth integration** via Gemini CLI — achieving paritly with OpenClaw architecture.

---

## Table of Contents

- [Architecture](#architecture)
- [The Agent Model](#the-agent-model)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Multi-Agent Ecosystem](#multi-agent-ecosystem)
- [Hybrid Hybrid Memory System (V2.1)](#hybrid-memory-system-v21)
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
│                    Brain Engine (V2.1)                      │
│  - Builds context: soul + user + Hybrid Search results      │
│  - Invokes gemini-cli subprocess with OAuth identity        │
│  - High-Fidelity Flush Cycle: save facts before compaction  │
│  - Native support for Gemini 3.0 Flash & 3.1 Pro            │
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
│                     │  │  └── memory/                    │
│                     │  │      ├── facts/                  │
│                     │  │      ├── journal/ (J & J-1)      │
│                     │  │      └── history/ (Summarized)   │
└─────────────────────┘  └─────────────────────────────────┘
```

For a complete technical deep-dive, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## The Agent Model

Every OpenBrain agent is composed of **three atomic primitives**:

### `soul.md` — Identity & Mission
The foundational document that defines what the agent *is*. It contains its purpose, its behavioral constraints, its communication style, and its proactive learning directives. The soul is loaded at the start of every inference call and forms the immutable identity layer of the agent.

### `user.md` — Interaction Protocol  
A human-authored document that specifies how the user wants to be addressed, their preferences, their background context, and any specific rules the agent must follow. This separates *who the agent is* from *how it should behave with this specific person*.

### `memory/` — Semantic Knowledge Base (V2.1)
A hierarchical, plain-text store that evolves throughout the lifetime of the agent:

| Path | Purpose |
|------|---------|
| `memory/facts/*.md` | Structured factual knowledge (High-fidelity content injection) |
| `memory/journal/YYYY-MM-DD.md` | Daily record (Today and Yesterday are reloaded into context) |
| `memory/history/conversation_history.json` | Rolling window of recent turns |
| `memory/history/history_summary.txt` | LLM-generated summary (triggered by token-budget) |
| `index.md` | Human-readable table of contents linking all facts |

---

## Installation

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | Standard library + SQLite FTS5 |
| [gemini-cli](https://github.com/google-gemini/gemini-cli) | 0.35+ | Logged in via `gemini login` |
| Telegram Bot Token | — | Per-agent bot from @BotFather |
| OAuth Identity | — | Persistent session in `~/.gemini/` |

### Steps (Zéro-Config)

```bash
# 0. Connexion au Gemini CLI (Mandatoire)
gemini login

# 1. Clone & Installation
git clone https://github.com/gauthierstrich/openbrain.git
cd openbrain
pip install -r requirements.txt

# 2. Setup Assistant (Automatique)
# Pour configurer vos tokens Telegram en mode guidé
bash scripts/ob-init.sh

# 3. Lancement
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

## Hybrid Memory System (V2.1)

OpenBrain's memory system is designed for **longevity and human readability**.

### Memory Flush (Self-Preservation)
Before the episodic history is summarized (to save tokens), the engine triggers a silent **Flush Turn**. The agent is forced to identify and save critical information from the current conversation into `memory/facts/` or the daily journal. This ensures no high-fidelity detail is lost during compaction.

### High-Fidelity Context Injection
Unlike RAG systems that only retrieve fragments, OpenBrain V2.1 injects:
- **Journals**: Content from today and yesterday for seamless inter-session continuity.
- **Facts**: Full content of relevant markdown fact files (up to context limits).

### Token-Based Compaction
History is no longer compressed based on a fixed message count, but on a **Token Budget (~8000 tokens)**. This ensures stability for agents with long, complex interactions.

---

## Configuration Reference

All runtime configuration is managed via a single `.env` file at the project root.

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_MODEL` | Yes | Model identifier (e.g., `gemini-1.5-pro`) |
| `BRAIN_STORAGE_PATH` | Yes | Absolute path to the directory containing the `agents/` folder |
| `ALLOWED_USER_ID` | Yes | Telegram user ID of the authorized user |
| `USER_LANGUAGE` | No | Response language code (default: `fr`) |
| `TELEGRAM_TOKEN_<AGENT>` | Yes (per agent) | Bot token for each agent (e.g., `TELEGRAM_TOKEN_PERSONAL`) |

See [`.env.example`](.env.example) for a complete reference.

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
