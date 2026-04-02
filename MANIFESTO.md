# The OpenBrain Manifesto

## The Problem with Memory

Every meaningful conversation you have with an AI resets to zero.

You explain your background, your goals, your preferences — again and again, to a system that has been deliberately designed to forget. This isn't a technical limitation. It's an architectural choice made to simplify cloud infrastructure and minimize state management complexity. The cost of that choice is paid entirely by the user.

Beyond the friction of repetition, there is a deeper issue: **data sovereignty**. When your personal history, your professional context, your private reflections live in a cloud database you don't control, they are subject to policies you didn't write, breaches you can't prevent, and business decisions you have no visibility into.

We built OpenBrain because we believe a different model is possible.

---

## Our Principles

### 1. Intelligence should belong to the individual

An AI agent that knows you — your goals, your habits, your context — is a fundamentally different tool than one that doesn't. That knowledge is yours. It should live on your hardware, in files you can read, edit, back up, or delete at any time.

OpenBrain stores everything as Markdown files on your local filesystem. There is no database, no cloud sync, no telemetry. If you want to inspect your agent's memory, you open a folder.

### 2. Configuration should happen through conversation

The barrier to entry for most AI infrastructure tools is prohibitive. YAML configuration files, API key management, vector database setup, embedding models — this complexity excludes the vast majority of potential users.

OpenBrain inverts this model. The system configures itself. You talk to an Architect agent in plain language; it provisions the infrastructure. Every internal operation — creating agents, writing memory, updating the knowledge index — is handled by the AI itself, not by the user.

### 3. Memory should be proactive, not manual

The best human assistants don't wait to be told what to remember. They recognize when information is important and retain it without being asked.

OpenBrain agents are designed with the same discipline. During every conversation, an agent actively monitors for new information — a deadline, a preference, a biographical detail — and writes it to its knowledge base silently, in the background. Over time, with no manual effort from the user, the agent builds a complete picture of the person it serves.

### 4. The system should outlast its components

AI models improve rapidly. Infrastructure choices made today may be suboptimal in six months. OpenBrain is designed for **model-agnosticism**: the memory system is pure Markdown, readable by any future model. The agent architecture makes no assumptions about the underlying LLM. Swapping the intelligence layer requires changing a single environment variable.

---

## What We Are Building

OpenBrain is not an app. It is a **framework** — a set of conventions, runtime components, and interaction patterns that allow anyone to deploy a persistent, locally-hosted AI agent that genuinely knows them.

The current implementation is a foundation. The principles above will guide every design decision we make as the system evolves.

We are building this in the open because the problems it addresses — memory persistence, data sovereignty, configuration ergonomics — are universal. The solutions should be too.

---

## 🚀 Native Intelligence: Zero-Bridge Execution (V2.0)
With the latest **Memory Orchestration V2.0**, OpenBrain agents now feature a proactive **Flush Cycle**. Before any conversational history is summarized, the agent performs a silent self-preservation pass to ensure all durable knowledge is committed to your local filesystem. 

---

*OpenBrain is MIT licensed. Fork it, adapt it, make it yours.*
