# 🏗️ OpenBrain Architecture: The High-Fidelity Infrastructure

## 1. Modular State Separation
OpenBrain follows a **memory-centric** architectural pattern, segregating identity from procedural logic.

- **The Static Soul**: A persistent, immutable-during-session Markdown file (`soul.md`) that represents the personality, mission, and constraints of the agent instance.
- **The Protocol Layer**: The `user.md` file defines the interaction standards, tone, and specific preferences of the human partner.
- **The Dynamic Memory**: A semantic knowledge base stored in a hierarchical file structure (`memory/facts/`, `memory/journal/`, `memory/history/`).

## 2. Intelligence Orchestration: Native Subprocess Execution
OpenBrain Core utilizes a **synchronous-over-asynchronous** approach for LLM orchestration.

- **The Engine (`brain.py`)**: Interacts with the **Gemini CLI** via `subprocess.run()`. This ensures that the agent inherits the machine's environment and natively supports tool usage (file reading, writing, and OS exploration) through the `--yolo` mode of the CLI.
- **Context Management**: The engine maintains a rolling-window of conversation history. When the token count exceeds the threshold, an "Episodic Summary" is generated and stored to preserve long-term context while minimizing latent cost.

## 3. The Proactive "YOLO" Learning Cycle
Unlike traditional RAG systems, OpenBrain Core is **active**.

- **Perception**: The agent uses native tools (e.g., `READ_PATH`) to explore local directories.
- **Cognition**: The engine analyzes the retrieved data against its current knowledge base.
- **Ingestion**: If the information is deemed critical, the agent autonomously executes a `SAVE_FACT` action, updating its own memory files without requiring human approval or "Zero-Terminal" intervention.

## 4. Multi-Interface Synchronization
The core is interface-agnostic. It currently supports:
- **Telegram Protocol**: A high-performance, mobile-ready interface with interactive reflection jobs.
- **Unified Supervisor**: The `ob-start.py` script manages the parallel lifecycle of multiple agents, ensuring stable execution and automatic restarting on failure.

---
*OpenBrain Core Architecture — Precision Engineering for Intelligence.*
