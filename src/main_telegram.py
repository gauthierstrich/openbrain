#!/usr/bin/env python3
"""
OpenBrain — Telegram Agent (Multi-Bot)
Interface Telegram pour les agents OpenBrain.
Usage : python3 main_telegram.py [PERSONAL|AC20|MT28]

Chaque agent a son propre bot Telegram et son propre espace mémoire.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Importations Telegram
from telegram import Update, constants
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# Importer l'intelligence partagée
import brain

# ─── Configuration ──────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

# Détecter l'agent à lancer via argument CLI (défaut : PERSONAL)
AGENT_KEY = sys.argv[1].upper() if len(sys.argv) > 1 else "PERSONAL"

# Mapping des clés de token dans le .env
TOKEN_MAP = {
    "PERSONAL": "TELEGRAM_TOKEN_PERSONAL",
    "AC20": "TELEGRAM_TOKEN_AC20",
}

token_env_key = TOKEN_MAP.get(AGENT_KEY)
if not token_env_key:
    print(f"❌ Agent inconnu : {AGENT_KEY}. Agents disponibles : {list(TOKEN_MAP.keys())}")
    sys.exit(1)

TOKEN = os.getenv(token_env_key)
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")

# Configurer le Brain pour cet agent
brain.set_agent(AGENT_KEY)

# Configurer le logging
logging.basicConfig(
    format=f'%(asctime)s - [{AGENT_KEY}] %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Utilitaires d'Affichage ──────────────────────────────────────────

async def keep_typing(chat_id: int, context: ContextTypes.DEFAULT_TYPE, stop_event: asyncio.Event):
    """Envoie l'action 'Typing' en continu jusqu'à ce que stop_event soit activé."""
    while not stop_event.is_set():
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
            await asyncio.sleep(4)
        except Exception as e:
            logger.error(f"Erreur indicateur typing : {e}")
            break

# ─── Gestionnaires de Messages ───────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start"""
    user = update.effective_user
    user_id = str(user.id)

    if not ALLOWED_USER_ID:
        await update.message.reply_text(
            f"👋 Salut {user.first_name} !\n\nTon ID est : `{user_id}`\nConfigure-le dans ton `.env`.",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text("🚫 Accès refusé.")
        return

    agent_labels = {
        "PERSONAL": "🧠 **OpenBrain — Assistant Personnel**",
        "AC20": "🔬 **OpenBrain — AC20 (Data Science)**",
    }
    label = agent_labels.get(AGENT_KEY, f"🤖 **OpenBrain — {AGENT_KEY}**")

    await update.message.reply_text(
        f"{label} activé pour Gauthier.\nJe suis prêt.",
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Traite les messages texte entrants."""
    user = update.effective_user
    user_id = str(user.id)

    if not ALLOWED_USER_ID or user_id != ALLOWED_USER_ID:
        return

    text = update.message.text
    if not text:
        return

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.effective_chat.id, context, stop_typing))

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, brain.process_message, text)

        stop_typing.set()
        await typing_task

        try:
            await update.message.reply_text(response, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception as parse_error:
            logger.warning(f"Échec Markdown, envoi en texte brut : {parse_error}")
            await update.message.reply_text(response)
    except Exception as e:
        stop_typing.set()
        await typing_task
        logger.error(f"Erreur handle_message : {e}")
        await update.message.reply_text(f"❌ Désolé, une erreur est survenue : {e}")

# ─── Commandes spécifiques à l'Assistant Personnel ───────────────────

async def sync_apple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /sync pour Apple Rappels (uniquement agent PERSONAL et macOS)."""
    if AGENT_KEY != "PERSONAL":
        return

    user = update.effective_user
    if not ALLOWED_USER_ID or str(user.id) != ALLOWED_USER_ID:
        return

    # Détection de la plateforme pour /sync
    if sys.platform != "darwin":
        await update.message.reply_text("🐧 **Note :** La synchronisation des Rappels Apple est uniquement disponible sur macOS. Ubuntu ne supporte pas nativement ce capteur.", parse_mode=constants.ParseMode.MARKDOWN)
        return

    import sensors.apple_sync as apple_sync
    wait_msg = await update.message.reply_text("🔄 Synchronisation avec tes Rappels Apple en cours...")
    # ... rest of the function ...


# ─── Auto-Réflexion Proactive ───────────────────────────────────────

async def proactive_reflection_job(context: ContextTypes.DEFAULT_TYPE):
    """Tâche périodique d'auto-réflexion (uniquement agent PERSONAL)."""
    if not ALLOWED_USER_ID:
        return

    logger.info("Lancement de la routine d'auto-réflexion proactive...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, brain.self_reflect)

    if result != "NONE" and not result.startswith("[ERREUR"):
        logger.info(f"Message proactif généré : {result}")
        try:
            await context.bot.send_message(
                chat_id=ALLOWED_USER_ID,
                text=f"✦ {result}",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        except Exception as parse_error:
            logger.warning(f"Échec Markdown proactif : {parse_error}")
            await context.bot.send_message(chat_id=ALLOWED_USER_ID, text=f"✦ {result}")
    else:
        logger.info("Auto-réflexion terminée : Pas de message nécessaire.")

# ─── Main ────────────────────────────────────────────────────────────

async def post_init(application):
    """Configuration du menu de commandes Telegram."""
    commands = [("start", "Relancer l'assistant")]
    if AGENT_KEY == "PERSONAL":
        commands.append(("sync", "Synchroniser les devoirs (Apple Rappels)"))
    await application.bot.set_my_commands(commands)

def main():
    if not TOKEN:
        print(f"❌ Token manquant pour l'agent {AGENT_KEY} (variable : {token_env_key})")
        sys.exit(1)

    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    # Proactivité uniquement pour l'agent personnel
    # if AGENT_KEY == "PERSONAL" and application.job_queue:
    #     application.job_queue.run_repeating(proactive_reflection_job, interval=3600, first=60)

    # Gestionnaires
    application.add_handler(CommandHandler("start", start))
    if AGENT_KEY == "PERSONAL":
        application.add_handler(CommandHandler("sync", sync_apple))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print(f"🚀 OpenBrain [{AGENT_KEY}] lancé pour l'ID {ALLOWED_USER_ID}")
    application.run_polling(allowed_updates=[Update.MESSAGE])

if __name__ == "__main__":
    main()
