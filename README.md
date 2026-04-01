# OpenBrain 🧠 — Your Personal Agentic Second Brain

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status: v1.5.0](https://img.shields.io/badge/Status-v1.5.0-green.svg)]()
[![OS: macOS & Ubuntu](https://img.shields.io/badge/OS-macOS%20%26%20Ubuntu-orange.svg)]()

> **OpenBrain** is a high-fidelity, modular agentic ecosystem designed to manage your life history, academic goals, and professional aspirations through a locally-hosted "Second Brain" interface. Compatible with **macOS** and **Linux (Ubuntu)**, and powered by **Gemini 3 Flash & 3.1 Pro**, it bridges the gap between static notes and proactive digital assistance.


---

## 🌟 Key Features

*   **Modular Semantic Memory**: A hierarchical knowledge base built on human-readable Markdown. Optimized for high-recall RAG without the overhead of heavy vector databases.
*   **macOS Deep Integration**: Real-time synchronization with **Apple Reminders**, system monitoring, and terminal automation.
*   **Multi-Interface Orchestration**: Use it via a high-performance **CLI (Terminal)** or a proactive, mobile-ready **Telegram Bot**.
*   **Proactive Reflection**: The agent autonomously analyzes your goals (e.g., UTBM CC3 schedules, Quant Finance research) and chooses the right moment to intervene and support you.
*   **Rolling-Window Context**: Intelligent conversation summarization ensures it never forgets your long-term facts while staying lean on token costs.

---

## 🏗️ System Architecture

OpenBrain follows a **memory-centric** architectural pattern, separating logic from state.

```mermaid
graph LR
    User([User]) <--> UI[CLI / Telegram]
    UI <--> Brain[Brain Core]
    Brain <--> FS[(Second Brain FS)]
    Brain <--> LLM[Gemini 3 Flash & 3.1 Pro]
    FS --- Index[Global Index]
    FS --- Facts[Semantic Facts]
    FS --- Logs[Episodic Journal]
```

> [!NOTE]
> For a deep dive into the underlying data flow and memory stratification, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 🛠️ Getting Started (Zero-Friction Install)

### 1. Prerequisites
*   **macOS** (Required for Apple Reminders sync and native automation).
*   **Python 3.10+**
*   **[gemini-cli](https://github.com/google-gemini/gemini-cli)** installed and configured (`gemini login`).

### 2. Interactive Installation (The Wizard)
OpenBrain features a professional, interactive installation assistant that configures your environment in seconds.

```bash
git clone https://github.com/gauthierstrich/OpenBrain.git
cd OpenBrain
bash scripts/setup.sh
```

> [!TIP]
> The Wizard will ask for your **Second Brain location**, your **Telegram Bot Tokens**, and your **ID**. It handles all the `.env` configuration and folder creation for you.

---

## 🚀 Launching the Brain

OpenBrain supports multiple agents running in parallel, each with its own Telegram interface.

### A. One-Click Launch (Recommended)
Launch all your agents (Personal Assistant + Specialists) simultaneously:
```bash
bash scripts/start_agents.sh
```

### B. Manual Agent Launch
You can also launch agents individually:
```bash
# Telegram: Personal Assistant
python3 src/main_telegram.py PERSONAL

# Telegram: AC20 Specialist (Data Science)
python3 src/main_telegram.py AC20

# Terminal: Personal Assistant (CLI Mode)
python3 src/main_cli.py
```

---

## 🤖 Multi-Agent Ecosystem

OpenBrain is designed for modular intelligence.
1.  **Personal Assistant**: Manages your life, agenda, and high-level strategy.
2.  **Specialist Agents**: Experts in specific subjects (e.g., **AC20** for Data Science & Finance).
3.  **Cross-Agent Memory**: The Personal Assistant has "read-only" access to the progress files of all specialists to help you build global revision plans.


---

## 📖 Philosophical Core

OpenBrain is not a toy; it is an extension of your cognitive capacity. It adheres to three strict rules:
1.  **Privacy First**: Your memory lives on your machine, not in a cloud database.
2.  **Human Clarity**: All memory is stored in Markdown, readable by you at any time.
3.  **Strategic Support**: The agent focuses on your higher-level goals (Academic Excellence, Quant Fund Management) over trivial tasks.

---

## 🤝 Contributing & License

We value high-quality contributions. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

Distributed under the **MIT License**. See `LICENSE` for more information.

---
*Created by **Gauthier Strich** — UTBM TC4 Student & Quantitative Research Enthusiast.*
