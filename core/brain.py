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
    Implémente les patterns mémoire d'OpenClaw : Memory Flush, Journal Reload, Facts Loading.
    """
    def __init__(self):
        self.loader = AgentLoader()
        self.creator = AgentCreator()
        self.refresh_agents()
        self.current_agent = "personal" if "personal" in self.agents else (list(self.agents.keys())[0] if self.agents else None)

    def refresh_agents(self):
        self.agents = self.loader.scan()

    def set_agent(self, agent_key: str) -> bool:
        if agent_key in self.agents:
            self.current_agent = agent_key
            return True
        return False

    def get_active_agent(self):
        return self.agents.get(self.current_agent)

    def _read_file(self, path: Path) -> str:
        if path and path.exists(): return path.read_text(encoding="utf-8")
        return ""

    def _get_paths(self):
        agent = self.get_active_agent()
        if not agent: raise BrainError("Aucun agent actif.")
        mem_dir = agent.path / "memory"
        return {
            "index": agent.path / "index.md",
            "soul": agent.path / "soul.md",
            "user": agent.path / "user.md",
            "history": mem_dir / "history" / "conversation_history.json",
            "summary": mem_dir / "history" / "history_summary.txt",
            "journal": mem_dir / "journal",
            "facts": mem_dir / "facts",
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
        entry = f"\n### [{timestamp}]\n**{config.USER_NAME} :** {user_msg}\n\n**Agent :** {agent_msg}\n"
        if not log_file.exists(): log_file.write_text(f"# Journal du {today}\n", encoding="utf-8")
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

    # ─── OpenClaw P0 : Memory Flush (sauvegarde avant compaction) ─────
    def _memory_flush(self, history_to_flush: list):
        """Avant compaction : demander à Gemini de sauvegarder les faits importants.
        Inspiré du mécanisme flush-plan.ts d'OpenClaw."""
        if not history_to_flush:
            return
        paths = self._get_paths()
        text_block = "\n".join(
            f"{config.USER_NAME}: {ex['user']}\nAgent: {ex['agent']}"
            for ex in history_to_flush
        )
        today = datetime.now().strftime("%Y-%m-%d")
        flush_prompt = f"""[MEMORY FLUSH — Tour silencieux pré-compaction]

La conversation ci-dessous va être résumée et les détails seront perdus.
Ton rôle : identifier les FAITS IMPORTANTS, DURABLES ou UTILES et les sauvegarder
dans tes fichiers de mémoire AVANT qu'ils ne disparaissent.

[RÈGLES]
1. Sauvegarde les faits durables dans memory/facts/ (crée ou complète des fichiers .md).
2. Sauvegarde les notes éphémères dans memory/journal/{today}.md (APPEND uniquement).
3. Ne modifie JAMAIS soul.md, index.md ou user.md pendant un flush.
4. Si rien d'important à sauvegarder, ne fais rien.
5. N'écris AUCUNE réponse textuelle. Agis uniquement sur les fichiers.

[CONVERSATION À ANALYSER]
{text_block}
"""
        # Appel silencieux — on ignore le retour texte, seule l'écriture fichier compte
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

        # ✨ NOUVEAU : Chargement du contenu réel des faits (pattern OpenClaw)
        facts_content = self._load_facts_content()
        facts_section = f"=== MÉMOIRE FACTUELLE (facts/) ===\n{facts_content}" if facts_content else "=== MÉMOIRE FACTUELLE ===\n(Aucun fait sauvegardé pour l'instant)"

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
Pour mémoriser un fait important, écris-le dans memory/facts/<sujet>.md.
Pour les notes temporaires, ajoute-les dans memory/journal/{datetime.now().strftime('%Y-%m-%d')}.md.
Si {config.USER_NAME} te demande de prendre en compte un dossier extérieur, utilise tes outils natifs pour l'explorer et extraire les infos importantes vers tes propres fichiers dans {paths['facts']}.

[MESSAGE DE {config.USER_NAME}]
{user_message}

[INSTRUCTION FINALE]
Réponds en Français. Agis directement sur le système si nécessaire. Ne te répète pas.
"""
        return context

    def ask_gemini(self, prompt: str) -> str:
        paths = self._get_paths()
        try:
            # -y : YOLO (Approuve tous les outils)
            # --accept-raw-output-risk : Autorise les sorties potentiellement risquées (shell, file access)
            result = subprocess.run(["gemini", "-y", "--accept-raw-output-risk", "-m", config.GEMINI_MODEL], input=prompt.encode('utf-8'), capture_output=True, timeout=300, cwd=str(paths["storage"]), env=os.environ)
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
