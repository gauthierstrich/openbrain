# OpenBrain Setup Guide 🚀

This guide provides comprehensive instructions for deploying the OpenBrain agentic ecosystem on your machine.

## 📋 Prerequisites

To run OpenBrain securely and efficiently, ensure you have:
1.  **macOS 13.0+** (Required for native Apple Reminders synchronization).
2.  **Python 3.10+**.
3.  **Gemini CLI** installed and authenticated (`gemini auth login`).

---

## ⚡ Zero-Friction Installation (Recommended)

We provide an automated setup script that handles dependency resolution and repository structuring.

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/gauthierstrich/OpenBrain.git
    cd OpenBrain
    ```

2. **Run the Initialization Script**:
    ```bash
    ./scripts/setup.sh
    ```
    *This script will generate your `.env` file, install Python packages, and scaffold your local Second Brain directories.*

3. **Configure your Secrets**:
    Open the newly generated `.env` file and insert your Telegram Token and personal IDs.

---

## 🛠️ Manual Installation (Advanced)

If you prefer to configure the environment step-by-step:

1. **Virtual Environment Setup**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2. **Environment Variables**:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` to define your `BRAIN_STORAGE_PATH` (where the agent will store its semantic memory).

---

## 🔐 macOS Permissions (Crucial for Sync)

OpenBrain interacts with macOS APIs (Apple Events) to read your Reminders and execute local diagnostics.
When launching OpenBrain for the first time, macOS will prompt you:
> *"Terminal" wants to access "Reminders".*

**You MUST click "OK".**
If you miss the prompt or synchronization fails (Silent Timeouts):
1. Go to **System Settings > Privacy & Security > Automation**.
2. Under your Terminal application (or Python if running raw), ensure **Reminders** is toggled ON.

---

## 🚀 Deployment

### Interactive Orchestrator (CLI Mode)
For direct system interaction and debugging:
```bash
python3 src/main_cli.py
```

### Proactive Polling (Telegram Mode)
To run the agent in the background as a 24/7 proactive companion:
```bash
nohup python3 src/main_telegram.py > bot.log 2>&1 &
```

---
*OpenBrain v1.5.0 — Setup Engineering Document*
