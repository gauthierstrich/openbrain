# OpenBrain — V2.5 (Obsidian Edition)

> A local-first, modular multi-agent framework that transforms your personal knowledge into an autonomous, evolving intelligence — hosted entirely on your own machine.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Gemini%20CLI-4285F4)](https://github.com/google-gemini/gemini-cli)
[![Status: v2.5](https://img.shields.io/badge/Status-v2.5%20Stable-green)]()

---

## Overview

OpenBrain is an open-source **multi-agent cognitive framework** built around a fundamental principle: your intelligence should live on your machine, not in a corporate cloud.

Unlike SaaS-based AI assistants that reset between sessions, OpenBrain agents maintain **persistent, structured memory** across every conversation. Over time, each agent builds a rich semantic knowledge base about its user — autonomously, silently, and without requiring any manual curation.

**Version 2.5** introduces **Global User Identity** and an **Obsidian-Ready** filesystem architecture, ensuring your data is not only sovereign but also natively compatible with your personal knowledge management (PKM) tools.

---

## Key Features

- **Local-First Architecture**: All data — facts, journals, identity — is stored as plain Markdown files. No third-party databases. No telemetry.
- **Biographical Onboarding (V2.5)**: A dedicated Architect agent conducts an initial "Identity Session" to build your global profile (`identity/user.md`), sharing your goals and values across all specialized agents.
- **Hybrid Semantic Memory**: High-performance retrieval combining SQLite FTS5 (BM25) and Gemini Embeddings (Cosine Similarity).
- **Obsidian Native**: Memory structure follows Obsidian conventions (Callouts, Wikilinks, YAML Frontmatter), allowing you to browse your agent's mind as a standard vault.
- **Zero-Config Security**: Native OAuth integration via Gemini CLI — no manual API key management required.

---

## Architecture

OpenBrain follows a **memory-centric, event-driven** architecture. The system is designed to be stateless at the process level and stateful at the filesystem level.

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
│                    Brain Engine (V2.5)                      │
│  - Context: Global Identity + Agent Prefs + Hybrid Search   │
│  - Invokes gemini-cli subprocess with OAuth identity        │
│  - High-Fidelity Flush Cycle: save facts before compaction  │
│  - Native support for Gemini 1.5 Flash & Pro              │
└─────────────────────────────────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
┌─────────────────────┐  ┌─────────────────────────────────┐
│    Gemini CLI       │  │    Filesystem (Agent Memory)    │
│  (subprocess.run)   │  │                                 │
│  - Native file      │  │  agents/<name>/                 │
│    access tools     │  │  ├── 📓 01 - Journal/           │
│  - Internet access  │  │  ├── 🧠 02 - Mémoire/           │
│  - YOLO execution   │  │  ├── ⚙️ 03 - Configuration/     │
│                     │  │  └── 04 - Archives/              │
└─────────────────────┘  └─────────────────────────────────┘
```

---

## The Agent Model (V2.5)

Every OpenBrain agent is composed of three atomic primitives, now structured for the Obsidian ecosystem:

### ⚙️ 03 - Configuration
- **`soul.md`**: The foundational identity, mission, and behavioral constraints.
- **`user.md`**: Agent-specific interaction preferences (e.g., "be concise", "use formal tone").
- **`../../identity/user.md`**: The **Global Profile** containing your life objectives, background, and core values.

### 📓 01 - Journal
Daily episodic records formatted with Obsidian Callouts (`[!CHAT]`) and YAML metadata. Provides the agent with immediate context of recent interactions.

### 🧠 02 - Mémoire
Long-term factual knowledge base. Written by the agent during "Memory Flush" cycles to preserve critical information before conversation compaction.

---

## Installation

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | Standard library + SQLite FTS5 |
| [gemini-cli](https://github.com/google-gemini/gemini-cli) | 0.35+ | Logged in via `gemini login` |
| Telegram Bot Token | — | Per-agent bot from @BotFather |

### Quick Start

```bash
# 1. Clone & Setup
git clone https://github.com/gauthierstrich/openbrain.git
cd openbrain
pip install -r requirements.txt

# 2. Interactive Onboarding
# This will ask for your name and Telegram credentials
bash scripts/ob-init.sh

# 3. Launch the OS
python3 scripts/ob-start.py
```

After launching, open Telegram and send `/start` to your **Architect** bot. It will guide you through a biographical session to initialize your global profile.

---

## Configuration Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_MODEL` | Yes | Model identifier (e.g., `gemini-1.5-flash`) |
| `BRAIN_STORAGE_PATH` | Yes | Absolute path to your Second Brain directory |
| `ALLOWED_USER_ID` | Yes | Your Telegram user ID for access control |
| `TELEGRAM_TOKEN_ARCHITECT` | Yes | Bot token for the system configuration agent |

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
