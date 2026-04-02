# 🏗️ OpenBrain Architecture: The High-Fidelity Infrastructure

## 1. Modular State Separation
OpenBrain follows a **memory-centric** architectural pattern, segregating identity from procedural logic.

- **The Static Soul**: A persistent, immutable-during-session Markdown file (`soul.md`) that represents the personality, mission, and constraints of the agent instance.
- **The Protocol Layer**: The `user.md` file defines the interaction standards, tone, and specific preferences of the human partner.
- **The Dynamic Memory (V2.0)**: A high-fidelity cognitive storage system. It uses a tiered approach:
    - **Long-term Facts** (`memory/facts/*.md`): Durable knowledge with active content injection.
    - **Daily Logs** (`memory/journal/YYYY-MM-DD.md`): Temporal context with automatic multi-day reload (J and J-1).
    - **Episodic History** (`memory/history/`): Compressed conversational context with token-derived compaction.

## 2. Intelligence Orchestration: High-Fidelity Execution
OpenBrain Core utilizes a **synchronous-over-asynchronous** approach for LLM orchestration.

- **The Engine (`brain.py`)**: Interacts with the **Gemini CLI** via `subprocess.run()`. This ensures that the agent inherits the machine's environment and natively supports tool usage through the `--yolo` mode of the CLI.
- **Context Management (V2.0)**: The engine maintains a robust token-aware window.
    - **Token-based Compaction**: Compaction is triggered when the character-to-token budget (approx. 8000 tokens) is exceeded, ensuring stability for both long and short interactions.
    - **Context Injection**: At every turn, the engine automatically injects the content of recent journals and relevant fact files into the prompt, ensuring the agent has full situational awareness without manual search.

## 3. The Proactive "Memory Flush" Cycle
Unlike traditional passive systems, OpenBrain Core is **active and self-preserving**.

- **Perception**: The agent uses native tools to explore local directories.
- **Memory Flush**: Before the episodic history is summarized (compaction), the engine triggers a silent "Flush Turn". This forces the agent to identify and save critical information from the current conversation to the Markdown files in `facts/` or `journal/`.
- **Ingestion**: This ensures that even after a summary, the "finesse" of the information is preserved in durable storage.

## 4. Multi-Interface Synchronization
The core is interface-agnostic. It currently supports:
- **Telegram Protocol**: A high-performance, mobile-ready interface with interactive reflection jobs.
- **Unified Supervisor**: The `ob-start.py` script manages the parallel lifecycle of multiple agents, ensuring stable execution and automatic restarting on failure.

---
*OpenBrain Core Architecture — Precision Engineering for Intelligence.*
