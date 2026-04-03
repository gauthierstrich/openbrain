#!/usr/bin/env python3
import subprocess
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from core import config
from core.agent_loader import AgentLoader
from core.agent_creator import AgentCreator, AgentCreationError
from core.memory_index import MemoryIndex

class BrainError(Exception):
    pass

# ─── Constantes de compaction (inspirées d'OpenClaw compaction.ts) ────────
CHARS_PER_TOKEN = 3.5          # Approximation pour le français
COMPACTION_TOKEN_THRESHOLD = 8000   # Seuil en tokens avant déclenchement
COMPACTION_KEEP_RECENT = 15    # Nombre de messages récents à préserver
COMPACTION_CHAR_THRESHOLD = int(COMPACTION_TOKEN_THRESHOLD * CHARS_PER_TOKEN)

class Brain:
    """
    OpenBrain Core — Le Moteur Cognitif V2.0 (OpenClaw-Inspired Memory)
    Utilise la puissance native du Gemini CLI (YOLO + Tools) pour lire/écrire.
    Implémente les patterns mémoire d'OpenClaw : Memory Flush, Journal Reload, Hybrid Search.
    """
    def __init__(self):
        self.loader = AgentLoader()
        self.creator = AgentCreator()
        self.memory_index: MemoryIndex | None = None
        self.refresh_agents()
        self.current_agent = "personal" if "personal" in self.agents else (list(self.agents.keys())[0] if self.agents else None)
        self._init_memory_index()

    def refresh_agents(self):
        self.agents = self.loader.scan()

    def set_agent(self, agent_key: str) -> bool:
        if agent_key in self.agents:
            self.current_agent = agent_key
            self._init_memory_index()
            return True
        return False

    def _init_memory_index(self):
        """Initialise l'index hybride pour l'agent actif."""
        agent = self.get_active_agent()
        if agent:
            try:
                self.memory_index = MemoryIndex(agent.path)
                # Déclencher l'indexation complète au démarrage/changement d'agent
                self.memory_index.index_facts()
                self.memory_index.index_journals()
            except Exception:
                self.memory_index = None

    def get_active_agent(self):
        return self.agents.get(self.current_agent)

    def _read_file(self, path: Path) -> str:
        if path and path.exists(): return path.read_text(encoding="utf-8")
        return ""

    def _get_paths(self):
        agent = self.get_active_agent()
        if not agent: raise BrainError("Aucun agent actif.")
        
        # Structure Obsidian Premium (V2.5)
        return {
            "journal": agent.path / "📓 01 - Journal",
            "facts": agent.path / "🧠 02 - Mémoire",
            "config": agent.path / "⚙️ 03 - Configuration",
            "index": agent.path / "⚙️ 03 - Configuration" / "index.md",
            "soul": agent.path / "⚙️ 03 - Configuration" / "soul.md",
            "user": agent.path / "⚙️ 03 - Configuration" / "user.md",
            "history_dir": agent.path / "04 - Archives" / "history",
            "history": agent.path / "04 - Archives" / "history" / "conversation_history.json",
            "summary": agent.path / "04 - Archives" / "history" / "history_summary.txt",
            "storage": agent.path
        }

    # ─── Mémoire Épisodique (Interne) ──────────────────────────────────
    def load_history(self) -> list:
        p = self._get_paths()["history"]
        if p.exists():
            try: return json.loads(p.read_text(encoding="utf-8"))
            except: return []
        return []

    def save_history(self, history: list):
        p = self._get_paths()["history"]
        history = history[-50:]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_daily_log(self, user_msg: str, agent_msg: str):
        today = datetime.now().strftime("%Y-%m-%d")
        j_dir = self._get_paths()["journal"]
        j_dir.mkdir(parents=True, exist_ok=True)
        log_file = j_dir / f"{today}.md"
        timestamp = datetime.now().strftime("%H:%M")
        
        # Style Obsidian (V2.5) : YAML + Callouts
        if not log_file.exists(): 
            header = f"---\ntype: journal\ndate: {today}\ntags: [journal, openbrain]\n---\n# 📓 Journal du {today}\n"
            log_file.write_text(header, encoding="utf-8")
            
        entry = f"\n> [!CHAT] {timestamp}\n> **{config.USER_NAME} :** {user_msg}\n>\n> **Agent :** {agent_msg}\n"
        with open(log_file, "a", encoding="utf-8") as f: f.write(entry)

    # ─── OpenClaw P0 : Chargement des journaux récents (J et J-1) ─────
    def _load_recent_journals(self) -> str:
        """Charge le contenu des journaux d'aujourd'hui et d'hier (pattern OpenClaw)."""
        j_dir = self._get_paths()["journal"]
        if not j_dir.exists():
            return ""
        parts = []
        for delta in [0, 1]:  # Aujourd'hui, puis hier
            date_str = (datetime.now() - timedelta(days=delta)).strftime("%Y-%m-%d")
            journal_file = j_dir / f"{date_str}.md"
            if journal_file.exists():
                content = journal_file.read_text(encoding="utf-8").strip()
                if content:
                    label = "Aujourd'hui" if delta == 0 else "Hier"
                    parts.append(f"--- {label} ({date_str}) ---\n{content}")
        return "\n\n".join(parts)

    # ─── OpenClaw P0 : Chargement du contenu des faits ────────────────
    def _load_facts_content(self, max_total_chars: int = 6000) -> str:
        """Charge le contenu réel des fichiers facts/ (pas juste les noms)."""
        facts_dir = self._get_paths()["facts"]
        if not facts_dir.exists():
            return ""
        parts = []
        total = 0
        for f in sorted(facts_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                content = f.read_text(encoding="utf-8").strip()
                if total + len(content) > max_total_chars:
                    parts.append(f"\n[...{f.name} tronqué, total mémoire atteint]")
                    break
                parts.append(f"### 📄 {f.name}\n{content}")
                total += len(content)
        return "\n\n".join(parts)

    # ─── OpenClaw P2 : Recherche Hybride dans les faits ───────────────
    def _search_relevant_facts(self, query: str, top_k: int = 5) -> str:
        """Recherche les faits les plus pertinents via l'index hybride.
        Fallback sur le chargement brut si l'index est indisponible."""
        if self.memory_index:
            try:
                results = self.memory_index.search(query, top_k=top_k)
                if results:
                    parts = []
                    for r in results:
                        score_info = f"(pertinence: {r['score']:.0%})"
                        parts.append(f"### 📄 {r['filename']} {score_info}\n{r['content']}")
                    return "\n\n".join(parts)
            except Exception:
                pass
        # Fallback : chargement brut (comme V2.0 sans index)
        return self._load_facts_content()

    # ─── OpenClaw P0 : Memory Flush (sauvegarde avant compaction) ─────
    def _memory_flush(self, history_to_flush: list):
        """Avant compaction : demander à Gemini de sauvegarder les faits importants."""
        if not history_to_flush:
            return
        agent = self.get_active_agent()
        paths = self._get_paths()
        text_block = "\n".join(
            f"{config.USER_NAME}: {ex['user']}\nAgent: {ex['agent']}"
            for ex in history_to_flush
        )
        today = datetime.now().strftime("%Y-%m-%d")
        flush_prompt = f"""[MEMORY FLUSH — Tour silencieux pré-compaction]

La conversation ci-dessous va être résumée. Identifie les FAITS DURABLES et sauvegarde-les.
[FORMAT OBSIDIAN]
Chaque fichier de fait DOIT commencer par :
---
type: fait
tags: [memoire, {agent.name}]
updated: {today}
---
# 🧠 Fait : <Titre>
Puis le contenu. Utilise des [[Wikilinks]] si tu mentionnes d'autres sujets.
"""
        # Appel silencieux
        self.ask_gemini(flush_prompt)

    def _summarize_history(self, history: list) -> list:
        # ✨ P1 : Compaction basée sur le volume de tokens (pattern OpenClaw)
        total_chars = sum(len(ex.get('user', '')) + len(ex.get('agent', '')) for ex in history)
        if total_chars <= COMPACTION_CHAR_THRESHOLD:
            return history

        p = self._get_paths()["summary"]
        current_summary = self._read_file(p)
        to_summarize = history[:-COMPACTION_KEEP_RECENT]
        kept_history = history[-COMPACTION_KEEP_RECENT:]

        # ✨ NOUVEAU : Memory Flush avant compaction (pattern OpenClaw)
        self._memory_flush(to_summarize)

        text_to_summarize = ""
        for ex in to_summarize: text_to_summarize += f"{config.USER_NAME}: {ex['user']}\nAgent: {ex['agent']}\n\n"
        prompt = f"[RÉSUMÉ ACTUEL]\n{current_summary}\n\n[NOUVEAU]\n{text_to_summarize}\n\nRésume ultra-concis (max 4 phrases)."
        new_summary = self.ask_gemini(prompt)
        if not new_summary.startswith("[ERREUR"):
            p.write_text(new_summary, encoding="utf-8")
            self.save_history(kept_history)
            return kept_history
        return history

    # ─── Intelligence V2.0 (OpenClaw-Inspired Memory) ──────────────────
    def build_context(self, user_message: str, history: list) -> str:
        paths = self._get_paths()
        agent = self.get_active_agent()
        soul = self._read_file(paths["soul"])
        user_agent_prefs = self._read_file(paths["user"])
        index = self._read_file(paths["index"])
        summary = self._read_file(paths["summary"])
        global_user = self._read_file(config.IDENTITY_DIR / "user.md")

        recent = history[-15:]
        history_text = "=== HISTORIQUE RÉCENT ===\n" + "\n".join([f"> {config.USER_NAME}: {e['user']}\n> Toi: {e['agent']}\n" for e in recent]) if recent else ""

        # ✨ V2.0 : Recherche hybride dans les faits (pattern OpenClaw)
        facts_content = self._search_relevant_facts(user_message)
        facts_section = f"=== MÉMOIRE FACTUELLE (Pertinents pour ta question) ===\n{facts_content}" if facts_content else "=== MÉMOIRE FACTUELLE ===\n(Aucun fait sauvegardé pour l'instant)"

        # ✨ NOUVEAU : Chargement des journaux récents J/J-1 (pattern OpenClaw)
        journals_content = self._load_recent_journals()
        journals_section = f"=== JOURNAUX RÉCENTS ===\n{journals_content}" if journals_content else ""

        context = f"""
=== TON IDENTITÉ (SOUL) ===
{soul}

=== PROFIL UTILISATEUR ===
{global_user}

=== PRÉFÉRENCES D'INTERACTION ===
{user_agent_prefs}

{facts_section}

{journals_section}

=== RÉSUMÉ DU PASSÉ ===
{summary}

{history_text}

[CAPACITÉS NATIVES]
Tu es exécuté via le Gemini CLI avec accès complet au système.
Tu peux LIRE, ÉCRIRE, MODIFIER et SUPPRIMER des fichiers sur cette machine.

⚠️ SÉCURITÉ CRITIQUE : Pour toute modification d'un fichier Python (.py), tu DOIS impérativement utiliser le protocole de validation suivant :
1. Écris tes modifications dans un fichier temporaire (ex: /tmp/fix.py).
2. Vérifie la syntaxe avec la commande : `python3 core/code_guard.py --target <chemin_cible> --source /tmp/fix.py`
3. Si la commande échoue, analyse l'erreur de syntaxe fournie et recommence dans /tmp/fix.py.
Interdiction formelle de modifier un fichier .py directement avec `sed` ou au-dessus du fichier original sans cette validation.

[MESSAGE DE {config.USER_NAME}]
{user_message}

[INSTRUCTION FINALE]
Réponds en Français. Agis directement sur le système si nécessaire. Ne te répète pas.
"""
        return context

    def ask_gemini(self, prompt: str, use_pro: bool = False) -> str:
        paths = self._get_paths()
        model = config.GEMINI_PRO_MODEL if use_pro else config.GEMINI_MODEL
        try:
            # -y : YOLO (Approuve tous les outils)
            # --accept-raw-output-risk : Autorise les sorties potentiellement risquées (shell, file access)
            result = subprocess.run(["gemini", "-y", "--accept-raw-output-risk", "-m", model], input=prompt.encode('utf-8'), capture_output=True, timeout=300, cwd=str(paths["storage"]), env=os.environ)
            if result.returncode != 0: return f"[ERREUR Gemini] {result.stderr.decode('utf-8', errors='ignore').strip()}"
            return result.stdout.decode('utf-8', errors='ignore').strip()
        except: return "[ERREUR] Gemini CLI error."

    def process_message(self, user_input: str) -> str:
        if not self.get_active_agent(): return "❌ Agent inaccessible."
        history = self._summarize_history(self.load_history())
        context = self.build_context(user_input, history)
        response = self.ask_gemini(context)
        if not response.startswith("[ERREUR"):
            # Plus besoin de handle_system_actions (sauf pour des actions logiques complexes si besoin)
            history.append({"timestamp": datetime.now().isoformat(), "user": user_input, "agent": response})
            self.save_history(history)
            self.save_daily_log(user_input, response)
        return response

    def self_reflect(self) -> str: return "NONE"
