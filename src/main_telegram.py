#!/usr/bin/env python3
"""
OpenBrain — Telegram Agent
Interface Telegram pour l'agent OpenBrain.
Inclut : 
- Sécurité par ID
- Indicateur de frappe persistant (Typing)
- Auto-Réflexion Proactive (toutes les heures)
"""

import os
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
import sensors.apple_sync as apple_sync

# ─── Configuration ──────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")

# Configurer le logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Utilitaires d'Affichage ──────────────────────────────────────────

async def keep_typing(chat_id: int, context: ContextTypes.DEFAULT_TYPE, stop_event: asyncio.Event):
    """Envoie l'action 'Typing' en continu jusqu'à ce que stop_event soit activé."""
    while not stop_event.is_set():
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
            # L'indicateur Telegram dure environ 5 secondes, on répète toutes les 4s
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

    await update.message.reply_text(
        f"🧠 **OpenBrain** activé pour Gauthier.\nJe suis prêt et je vais t'envoyer des messages proactifs si nécessaire.",
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def sync_apple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /sync pour mettre à jour les rappels Apple."""
    user = update.effective_user
    user_id = str(user.id)

    if not ALLOWED_USER_ID or user_id != ALLOWED_USER_ID:
        return

    # Message d'attente
    wait_msg = await update.message.reply_text("🔄 Synchronisation avec tes Rappels Apple en cours...")

    try:
        # Exécution de la synchro sur le thread principal pour éviter les restrictions d'Apple Events sous macOS
        count = apple_sync.sync()

        if count >= 0:
            await wait_msg.edit_text(f"✅ Synchronisation terminée. **{count}** rappels UTBM trouvés.", parse_mode=constants.ParseMode.MARKDOWN)
        else:
            await wait_msg.edit_text("❌ Échec de la synchronisation (Erreur script).")
    except Exception as e:
        logger.error(f"Erreur /sync : {e}")
        await wait_msg.edit_text(f"❌ Erreur lors de la synchronisation : {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Traite les messages texte entrants."""
    user = update.effective_user
    user_id = str(user.id)

    if not ALLOWED_USER_ID or user_id != ALLOWED_USER_ID:
        return

    text = update.message.text
    if not text:
        return

    # Indicateur de frappe persistant pendant la réflexion de Gemini
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.effective_chat.id, context, stop_typing))

    try:
        # Exécuter l'appel Gemini (synchrone/subprocess) dans un exécuteur pour ne pas bloquer l'async
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, brain.process_message, text)
        
        # Arrêter le typing
        stop_typing.set()
        await typing_task

        # Tentative d'envoi en Markdown, sinon repli sur le format Texte brut
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

# ─── Auto-Réflexion Proactive ───────────────────────────────────────

async def proactive_reflection_job(context: ContextTypes.DEFAULT_TYPE):
    """Tâche périodique qui demande à l'agent s'il doit contacter l'utilisateur."""
    if not ALLOWED_USER_ID:
        return

    logger.info("Lancement de la routine d'auto-réflexion proactive...")
    
    # L'agent analyse sa mémoire et décide d'envoyer un message ou non
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, brain.self_reflect)

    if result != "NONE" and not result.startswith("[ERREUR"):
        logger.info(f"Message proactif généré : {result}")
        # Envoi du message à Gauthier avec fallback
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
        logger.info("Auto-réflexion terminée : Pas de message nécessaire pour l'instant.")

# ─── Main ────────────────────────────────────────────────────────────

async def post_init(application):
    """Configuration exécutée juste avant que le bot ne commence à écouter (ex: menu de commandes)."""
    await application.bot.set_my_commands([
        ("start", "Relancer l'assistant"),
        ("sync", "Synchroniser les devoirs (Apple Rappels)")
    ])

def main():
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN manquant !")
        return

    # Utilisation de post_init pour éviter l'erreur RuntimeError d'asyncio
    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    # Configuration de la file d'attente de tâches (Job Queue)
    # Ligne commentée à la demande de Gauthier pour désactiver le message auto toutes les 60 min
    # if application.job_queue:
    #     application.job_queue.run_repeating(proactive_reflection_job, interval=3600, first=60)
    #     print("⏰ Routine de proactivité configurée (toutes les 60 min)")

    # Gestionnaires
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sync", sync_apple))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print(f"🚀 OpenBrain Bot (Telegram) lancé pour l'ID {ALLOWED_USER_ID}")
    application.run_polling(allowed_updates=[Update.MESSAGE])

if __name__ == "__main__":
    main()
