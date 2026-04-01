#!/usr/bin/env python3
import subprocess
import json
import os
import re
from datetime import datetime
from pathlib import Path

from core import config
from core.agent_loader import AgentLoader
from core.agent_creator import AgentCreator, AgentCreationError

class BrainError(Exception):
    pass

class Brain:
    """
    OpenBrain Core — Le Moteur Cognitif V1.8 (Native Gemini Power)
    Utilise la puissance native du Gemini CLI (YOLO + Tools) pour lire/écrire.
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

    def _summarize_history(self, history: list) -> list:
        if len(history) <= 20: return history
        p = self._get_paths()["summary"]
        current_summary = self._read_file(p)
        to_summarize = history[:-15]
        kept_history = history[-15:]
        text_to_summarize = ""
        for ex in to_summarize: text_to_summarize += f"{config.USER_NAME}: {ex['user']}\nAgent: {ex['agent']}\n\n"
        prompt = f"[RÉSUMÉ ACTUEL]\n{current_summary}\n\n[NOUVEAU]\n{text_to_summarize}\n\nRésume ultra-concis (max 4 phrases)."
        new_summary = self.ask_gemini(prompt)
        if not new_summary.startswith("[ERREUR"):
            p.write_text(new_summary, encoding="utf-8")
            self.save_history(kept_history)
            return kept_history
        return history

    # ─── Intelligence V1.8 (Native Power) ─────────────────────────────
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

        # On donne à l'IA la liste des fichiers qu'elle PEUT aller lire si elle veut
        mem_files = [f.name for f in paths["facts"].iterdir()] if paths["facts"].exists() else []
        
        context = f"""
=== TON IDENTITÉ (SOUL) ===
{soul}

=== PROFIL UTILISATEUR ===
{global_user}

=== PRÉFÉRENCES D'INTERACTION ===
{user_agent_prefs}

=== STRUCTURE DE TA MÉMOIRE ACTUELLE ===
- Index : {paths['index']}
- Fichiers de faits disponibles : {", ".join(mem_files)}

=== RÉSUMÉ DU PASSÉ ===
{summary}

{history_text}

[CAPACITÉS NATIVES]
Tu es exécuté via le Gemini CLI avec accès complet au système.
Tu peux LIRE, ÉCRIRE, MODIFIER et SUPPRIMER des fichiers sur cette machine.
Si Gauthier te demande de prendre en compte un dossier extérieur, utilise tes outils natifs pour l'explorer et extraire les infos importantes vers tes propres fichiers dans {paths['facts']}.

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
