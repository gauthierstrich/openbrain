#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
import re
from pathlib import Path
from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from core import config
from core.brain import Brain

if len(sys.argv) < 2:
    print("❌ Usage: python3 -m core.interfaces.telegram <AGENT_NAME>")
    sys.exit(1)

AGENT_NAME = sys.argv[1].lower()
TOKEN_VAR = f"TELEGRAM_TOKEN_{AGENT_NAME.upper()}"
TOKEN = os.getenv(TOKEN_VAR)
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")

if not TOKEN:
    print(f"❌ Token manquant pour {AGENT_NAME} (configure la variable {TOKEN_VAR} dans .env)")
    sys.exit(1)

logging.basicConfig(
    format=f'%(asctime)s - [{AGENT_NAME}] %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

brain = Brain()
if not brain.set_agent(AGENT_NAME):
    print(f"❌ Agent '{AGENT_NAME}' introuvable dans le dossier 'agents/'.")
    sys.exit(1)

def clean_markdown(text: str) -> str:
    """Adapte le Markdown standard pour Telegram (Markdown V1)."""
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    text = re.sub(r'__(.*?)__', r'_\1_', text)
    return text

def get_architect_menu():
    keyboard = [
        [InlineKeyboardButton("🚀 Lancer l'Installation d'un Expert", callback_data="cmd:create_personal")],
        [InlineKeyboardButton("📂 Lister mes Experts", callback_data="cmd:list_agents")],
        [InlineKeyboardButton("👤 Configurer mon Profil", callback_data="cmd:setup_user")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def keep_typing(chat_id: int, context: ContextTypes.DEFAULT_TYPE, stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
            await asyncio.sleep(4)
        except Exception:
            break

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if ALLOWED_USER_ID and str(user.id) != ALLOWED_USER_ID:
        await update.message.reply_text("🚫 Accès refusé.")
        return

    agent = brain.get_active_agent()
    label = f"{agent.emoji} *OpenBrain — {agent.name.capitalize()}*" if agent else f"🤖 *OpenBrain — {AGENT_NAME.capitalize()}*"
    
    reply_markup = get_architect_menu() if AGENT_NAME == "architect" else None
    
    await update.message.reply_text(
        clean_markdown(f"{label} activé pour {config.USER_NAME}.\nJe suis prêt."),
        parse_mode=constants.ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if ALLOWED_USER_ID and str(user_id) != ALLOWED_USER_ID:
        return

    data = query.data

    loop = asyncio.get_event_loop()
    
    pending_signal = config.ROOT_DIR / "pending_restart.signal"

    if data == "cmd:create_personal":
        await query.edit_message_text(text="⏳ *Patiente un instant...*", parse_mode=constants.ParseMode.MARKDOWN)
        # On dit à l'architecte de commencer un processus hyper pédagogique
        response = await loop.run_in_executor(None, brain.process_message, "L'utilisateur veut installer un nouvel agent. Présente-toi comme l'Architecte Pédagogue et guide-le pas à pas. Demande d'abord quelle est la mission de l'agent. Explique simplement pourquoi on a besoin de ça.")
        final_response = f"🏗️ Commande d'installation reçue...\n\n{clean_markdown(response)}"
        try:
            await query.edit_message_text(text=final_response, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception:
            await query.edit_message_text(text=final_response)
            
    elif data == "cmd:list_agents":
        await query.edit_message_text(text="⏳ *Recherche des experts...*", parse_mode=constants.ParseMode.MARKDOWN)
        response = await loop.run_in_executor(None, brain.process_message, "L'utilisateur veut voir un récapitulatif pédagogique de la liste des agents qu'il a installés et à quoi ils servent.")
        final_response = f"📂 {clean_markdown(response)}"
        try:
            await query.edit_message_text(text=final_response, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception:
            await query.edit_message_text(text=final_response)
            
    elif data == "cmd:setup_user":
        try:
            await query.edit_message_text(text="Comment souhaites-tu que je t'appelle ? Écris-moi simplement ton prénom.")
        except Exception:
            pass

    if pending_signal.exists():
        os.rename(pending_signal, config.ROOT_DIR / "restart.signal")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if ALLOWED_USER_ID and str(user.id) != ALLOWED_USER_ID:
        return

    text = update.message.text
    if not text: return

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.effective_chat.id, context, stop_typing))

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, brain.process_message, text)
        stop_typing.set()
        await typing_task

        final_response = clean_markdown(response)
        try:
            await update.message.reply_text(final_response, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(final_response)
            
        pending_signal = config.ROOT_DIR / "pending_restart.signal"
        if pending_signal.exists():
            os.rename(pending_signal, config.ROOT_DIR / "restart.signal")
            
    except Exception as e:
        stop_typing.set()
        await typing_task
        await update.message.reply_text(f"❌ Erreur : {e}")

async def proactive_reflection_job(context: ContextTypes.DEFAULT_TYPE):
    if not ALLOWED_USER_ID: return
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, brain.self_reflect)
    
    if result != "NONE" and not result.startswith("[ERREUR"):
        final_result = clean_markdown(result)
        try:
            await context.bot.send_message(
                chat_id=ALLOWED_USER_ID, text=f"✦ {final_result}", parse_mode=constants.ParseMode.MARKDOWN
            )
        except Exception:
            await context.bot.send_message(chat_id=ALLOWED_USER_ID, text=f"✦ {final_result}")

async def post_init(application):
    commands = [("start", "Ouvrir l'Installateur et le Menu Principal")]
    await application.bot.set_my_commands(commands)

def main():
    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    if AGENT_NAME == "personal" and application.job_queue:
        application.job_queue.run_repeating(proactive_reflection_job, interval=5400, first=60)
        
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print(f"🚀 Telegram Agent [{AGENT_NAME}] lancé pour l'ID {ALLOWED_USER_ID or 'Public'}")
    application.run_polling(allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY])

if __name__ == "__main__":
    main()
