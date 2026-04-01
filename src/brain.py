#!/usr/bin/env python3
"""
OpenBrain — Brain (Le Cerveau)
Logique centrale partagée entre le Terminal et Telegram.
Gère la mémoire, le contexte et l'appel à Gemini CLI.
Supporte le multi-agent : chaque agent a son propre espace mémoire.
"""

import subprocess
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ─── Configuration des Chemins (Vers le Second Brain Multi-Agents) ─────
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

# Définition du stockage : Priorité au .env, sinon fallback
raw_storage = os.getenv("BRAIN_STORAGE_PATH", str(Path.home() / "Documents/Second Brain/OpenBrain"))
STORAGE_ROOT = Path(os.path.expanduser(raw_storage))

# ─── Configuration Multi-Agent ─────────────────────────────────────────

# Registre des agents connus et de leur type de chemins
AGENT_REGISTRY = {
    "PERSONAL": {
        "storage_dir": "Assistant_Personnel",
        "type": "personal",
    },
    "AC20": {
        "storage_dir": "Academie/AC20",
        "type": "academic",
    },
}

def get_agent_paths(agent_key="PERSONAL"):
    """Génère les chemins absolus pour un agent spécifique."""
    config = AGENT_REGISTRY.get(agent_key, AGENT_REGISTRY["PERSONAL"])
    agent_dir = STORAGE_ROOT / config["storage_dir"]

    if config["type"] == "personal":
        return {
            "soul": agent_dir / "Identité" / "soul.md",
            "user": agent_dir / "Identité" / "user.md",
            "index": agent_dir / "Identité" / "index.md",
            "daily": agent_dir / "Souvenirs" / "Journal",
            "shared": agent_dir / "Souvenirs" / "Partage" / "status.json",
            "history": agent_dir / "Souvenirs" / "Historique" / "conversation_history.json",
            "summary": agent_dir / "Souvenirs" / "Historique" / "history_summary.txt",
            "agenda": agent_dir / "Souvenirs" / "Faits" / "agenda_devoirs.md",
            "avancement": None,  # Pas d'avancement pour l'assistant personnel
            "storage": agent_dir,
        }
    else:  # academic
        return {
            "soul": agent_dir / "Identite" / "soul.md",
            "user": agent_dir / "Identite" / "user.md",
            "index": agent_dir / "Identite" / "index.md",
            "daily": agent_dir / "Souvenirs" / "Journal",
            "shared": None,
            "history": agent_dir / "Souvenirs" / "Historique" / "conversation_history.json",
            "summary": agent_dir / "Souvenirs" / "Historique" / "history_summary.txt",
            "agenda": None,
            "avancement": agent_dir / "avancement.md",
            "storage": agent_dir,
        }

# Agent par défaut (peut être changé au runtime)
CURRENT_AGENT = "PERSONAL"
P = get_agent_paths(CURRENT_AGENT)

def set_agent(agent_key: str):
    """Change l'agent actif à la volée."""
    global CURRENT_AGENT, P
    CURRENT_AGENT = agent_key
    P = get_agent_paths(agent_key)

# ─── Fonctions Utilitaires ─────────────────────────────────────────────

def read_file(path) -> str:
    """Lit un fichier texte. Retourne '' si le fichier n'existe pas ou est None."""
    if path is None:
        return ""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

def load_history() -> list:
    """Charge l'historique des conversations récentes."""
    if P["history"].exists():
        try:
            data = json.loads(P["history"].read_text(encoding="utf-8"))
            return data
        except json.JSONDecodeError:
            return []
    return []

def save_history(history: list):
    """Sauvegarde l'historique des conversations."""
    limit = 50
    history = history[-limit:]
    P["history"].parent.mkdir(parents=True, exist_ok=True)
    P["history"].write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def save_daily_log(user_msg: str, agent_msg: str):
    """Ajoute l'échange dans le journal quotidien."""
    today = datetime.now().strftime("%Y-%m-%d")
    P["daily"].mkdir(parents=True, exist_ok=True)
    log_file = P["daily"] / f"{today}.md"

    timestamp = datetime.now().strftime("%H:%M")
    entry = f"\n### [{timestamp}]\n**Gauthier :** {user_msg}\n\n**Agent :** {agent_msg}\n"

    mode = 'a' if log_file.exists() else 'w'
    with open(log_file, mode, encoding="utf-8") as f:
        if mode == 'w':
            f.write(f"# Journal du {today}\n")
        f.write(entry)

def load_summary() -> str:
    """Charge le résumé de l'historique."""
    if P["summary"].exists():
        return P["summary"].read_text(encoding="utf-8")
    return ""

def save_summary(summary: str):
    """Sauvegarde le résumé global."""
    P["summary"].parent.mkdir(parents=True, exist_ok=True)
    P["summary"].write_text(summary, encoding="utf-8")

def summarize_history(history: list) -> list:
    """
    Si l'historique dépasse 20 messages, on résume les plus anciens, on met à jour
    history_summary.txt, et on ne retourne que les 15 derniers messages.
    """
    if len(history) <= 20:
        return history

    to_summarize = history[:-15]
    kept_history = history[-15:]

    current_summary = load_summary()

    text_to_summarize = ""
    for ex in to_summarize:
        text_to_summarize += f"Gauthier: {ex['user']}\nAgent: {ex['agent']}\n\n"

    prompt = f"""
[ACTUEL RÉSUMÉ]
{current_summary}

[NOUVEAUX ÉCHANGES]
{text_to_summarize}

MISSION : Rédige en français un résumé ultra-concis (max 4 phrases) fusionnant le résumé actuel et ces nouveaux échanges.
Garde UNIQUEMENT les faits réels, les tâches en cours, le contexte actuel. Aucun bavardage.
RÈGLE : Ne donne QUE le résumé final, sans introduction.
"""
    new_summary = ask_gemini(prompt)
    if not new_summary.startswith("[ERREUR"):
        save_summary(new_summary)
        save_history(kept_history)
        return kept_history
    return history  # fail-safe

# ─── Intelligence ──────────────────────────────────────────────────────

def build_context(user_message: str, history: list) -> str:
    """Construit le prompt envoyé à Gemini, adapté à l'agent actif."""
    soul = read_file(P["soul"])
    user_profile = read_file(P["user"])
    memory_index = read_file(P["index"])
    summary = load_summary()

    # Blocs optionnels selon le type d'agent
    agenda = read_file(P.get("agenda")) if P.get("agenda") else ""
    avancement = read_file(P.get("avancement")) if P.get("avancement") else ""

    # Fenêtre de contexte
    recent = history[-15:]
    history_text = ""
    if recent:
        history_text = "=== HISTORIQUE RÉCENT ===\n"
        for exchange in recent:
            history_text += f"> Gauthier: {exchange['user']}\n> Toi: {exchange['agent']}\n\n"

    summary_block = f"=== RÉSUMÉ DU CONTEXTE GLOBAL ===\n{summary}\n" if summary else ""
    agenda_block = f"[CONTEXTE : AGENDA & DEVOIRS]\n{agenda}\n" if agenda else ""
    avancement_block = f"[CONTEXTE : AVANCEMENT DU PROJET]\n{avancement}\n" if avancement else ""

    # Charger les avancements des autres agents pour l'agent personnel (vue panoramique)
    cross_agent_block = ""
    if CURRENT_AGENT == "PERSONAL":
        for key, cfg in AGENT_REGISTRY.items():
            if key == "PERSONAL":
                continue
            av_path = STORAGE_ROOT / cfg["storage_dir"] / "avancement.md"
            av_content = read_file(av_path)
            if av_content:
                cross_agent_block += f"[AVANCEMENT {key}]\n{av_content}\n\n"

    context = f"""
{soul}

[CONTEXTE : PROFIL DE L'UTILISATEUR]
{user_profile}

{agenda_block}

{avancement_block}

[CONTEXTE : INDEX DES FICHIERS MÉMOIRE]
{memory_index}

{cross_agent_block}

{summary_block}

{history_text}

[MESSAGE ACTUEL DE GAUTHIER]
{user_message}

[INSTRUCTIONS STRICTES DO NOT VIOLATE]
- Langue: Français uniquement.
- Ton: Humain, franc, percutant, ultra-concis.
- Format Markdown: Telegram compatible (**gras**, `-` liste, pas de symboles `#`).
- Exécution: N'annonce JAMAIS tes actions (ex: "Je vais lire"), fournis la réponse immédiatement.
"""
    return context

def ask_gemini(prompt: str) -> str:
    """Appelle Gemini CLI en mode non-interactif."""
    try:
        result = subprocess.run(
            ["gemini", "-p", prompt, "-y", "-m", "gemini-3-flash-preview"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(P["storage"])
        )
        if result.returncode != 0:
            return f"[ERREUR Gemini CLI] {result.stderr.strip()}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[ERREUR] Gemini CLI n'a pas répondu dans les temps."
    except FileNotFoundError:
        return "[ERREUR] Gemini CLI n'est pas installé ou pas dans le PATH."

# ─── Orchestration ─────────────────────────────────────────────────────

def process_message(user_input: str) -> str:
    """Traite un message entrant de l'utilisateur."""
    history = load_history()
    history = summarize_history(history)
    context = build_context(user_input, history)
    response = ask_gemini(context)

    if not response.startswith("[ERREUR"):
        exchange = {
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "agent": response
        }
        history.append(exchange)
        save_history(history)
        save_daily_log(user_input, response)

    return response

def self_reflect() -> str:
    """L'agent analyse sa situation et décide s'il doit contacter Gauthier."""
    soul = read_file(P["soul"])
    user_profile = read_file(P["user"])
    memory_index = read_file(P["index"])
    history = load_history()

    recent = history[-5:]
    history_text = ""
    if recent:
        history_text = "\n## Derniers échanges\n"
        for exchange in recent:
            history_text += f"**Gauthier :** {exchange['user']}\n"
            history_text += f"**Toi :** {exchange['agent']}\n\n"

    prompt = f"""
=== TON IDENTITÉ (SOUL) ===
{soul}

=== PROFIL DE GAUTHIER ===
{user_profile}

=== TA MÉMOIRE ===
{memory_index}

{history_text}

=== MISSION D'AUTO-RÉFLEXION ===
Tu es en mode "proactif". Analyse les informations ci-dessus.
Décide s'il est pertinent de lui envoyer un message TOUT DE SUITE pour :
1. Lui rappeler une tâche urgente.
2. Lui donner un conseil d'organisation.
3. Prendre des nouvelles d'un projet en cours.
4. L'encourager s'il a beaucoup travaillé.

=== RÈGLES DE RÉPONSE ===
- **LANGUE :** Français uniquement.
- Si tu décides d'envoyer un message : Commence ta réponse par "SEND: " suivi du message court.
- **FORMATAGE :** Pas de titres `#`, utilise du **gras**.
- Si rien n'est urgent : Réponds EXACTEMENT "NONE".
"""
    response = ask_gemini(prompt)

    if response.startswith("SEND: "):
        message = response.replace("SEND: ", "").strip()
        history.append({
            "timestamp": datetime.now().isoformat(),
            "user": "[PROACTIF / AUTO-RÉFLEXION]",
            "agent": message
        })
        save_history(history)
        save_daily_log("[PROACTIF]", message)
        return message

    return "NONE"

if __name__ == "__main__":
    print("Test du cerveau OpenBrain...")
    res = process_message("Test de connexion au cerveau.")
    print(f"Réponse : {res}")
