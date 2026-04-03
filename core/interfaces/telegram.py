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

def format_as_html(text: str) -> str:
    """Transforme le Markdown de l'IA en HTML propre pour Telegram et retire le bruit technique."""
    import re
    # 1. Filtre agressif des pensées internes
    skip_patterns = [
        r"^[iI] will.*", r"^[iI]'ll.*", r"^[iI] am going to.*", r"^[jJ]e vais.*",
        r"^[jJ]e m'apprête à.*", r"^[sS]earching.*", r"^[rR]eading.*", r"^[cC]hecking.*",
        r"^[eE]xploration.*", r"^[uU]using tool.*", r"^[aA]ppel de l'outil.*",
        r"^[vV]érification.*", r"^[lL]ecture du fichier.*", r"^[fF]aisons un.*",
        r"^\[SYSTEM:.*\]", r"^\[DEBUG\]", r"^\[INFO\]", r"^\[CAPACITÉS NATIVES\]",
        r"^===.*===$"
    ]
    
    # Nettoyage des pensées même en milieu de bloc si elles sont isolées
    text = re.sub(r'(?:\n|^)(?:[jJ]e vais|[iI] will|[iI]\'ll).*?\.(?:\n|$)', '\n', text)
    
    lines = text.split('\n')
    filtered_lines = []
    
    for line in lines:
        l_strip = line.strip()
        if not l_strip:
            if filtered_lines and filtered_lines[-1] != "": filtered_lines.append("")
            continue
            
        # Si la ligne matche un pattern de "pensée" et est courte, on l'ignore
        if any(re.match(p, l_strip, re.IGNORECASE) for p in skip_patterns) and len(l_strip) < 250:
            continue
            
        filtered_lines.append(line)
    
    text = '\n'.join(filtered_lines).strip()
    
    # 2. Conversion Markdown -> HTML
    # Échappement des caractères spéciaux HTML
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # Remplacements Markdown standards
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = re.sub(r'### (.*)', r'<b>\1</b>', text)
    
    # Séparateur visuel élégant
    text = text.replace("---", "────────────────")
    
    # Nettoyage final des sauts de ligne excessifs
    text = re.sub(r'\n{3,}', '\n\n', text)
        
    return text.strip()

def split_message(text: str, limit: int = 4000) -> list[str]:
    """Découpe un message trop long en plusieurs parties en respectant les limites de Telegram."""
    if len(text) <= limit:
        return [text]
    
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        
        # Chercher le dernier saut de ligne avant la limite
        split_at = text.rfind('\n', 0, limit)
        if split_at == -1:
            split_at = limit
            
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
        
    return parts

async def send_safe_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None):
    """Envoie une réponse de manière sécurisée (découpage si trop long)."""
    parts = split_message(text)
    for i, part in enumerate(parts):
        # On n'ajoute le menu que sur le dernier message
        markup = reply_markup if i == len(parts) - 1 else None
        try:
            if update.callback_query:
                if i == 0:
                    await update.callback_query.edit_message_text(text=part, parse_mode=constants.ParseMode.HTML, reply_markup=markup)
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=part, parse_mode=constants.ParseMode.HTML, reply_markup=markup)
            else:
                await update.message.reply_text(part, parse_mode=constants.ParseMode.HTML, reply_markup=markup)
        except Exception:
            # Fallback sans HTML si erreur de parsing
            if update.callback_query:
                if i == 0:
                    await update.callback_query.edit_message_text(text=part, reply_markup=markup)
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=part, reply_markup=markup)
            else:
                await update.message.reply_text(part, reply_markup=markup)

def get_architect_menu():
    keyboard = [
        [InlineKeyboardButton("🚀 Installer un Expert", callback_data="cmd:create_personal")],
        [InlineKeyboardButton("📂 Liste des Experts", callback_data="cmd:list_agents")],
        [InlineKeyboardButton("👤 Mon Profil", callback_data="cmd:setup_user")]
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
    body = f"Système activé pour <b>{config.USER_NAME}</b>.\nJe suis prêt à t'accompagner."
    reply_markup = get_architect_menu() if AGENT_NAME == "architect" else None
    await update.message.reply_text(body, parse_mode=constants.ParseMode.HTML, reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if ALLOWED_USER_ID and str(user_id) != ALLOWED_USER_ID: return
    data = query.data
    loop = asyncio.get_event_loop()
    pending_signal = config.ROOT_DIR / "pending_restart.signal"
    
    if data == "cmd:create_personal":
        await query.edit_message_text(text="⏳ <i>Initialisation du protocole d'architecture...</i>", parse_mode=constants.ParseMode.HTML)
        response = await loop.run_in_executor(None, brain.process_message, "L'utilisateur veut installer un nouvel agent. Présente-toi comme l'Architecte Pédagogue et guide-le pas à pas. Demande d'abord quelle est la mission de l'agent. Explique simplement pourquoi on a besoin de ça.")
        await send_safe_message(update, context, format_as_html(response))
    elif data == "cmd:list_agents":
        await query.edit_message_text(text="⏳ <i>Recherche de tes experts actifs...</i>", parse_mode=constants.ParseMode.HTML)
        response = await loop.run_in_executor(None, brain.process_message, "L'utilisateur veut voir un récapitulatif pédagogique de la liste des agents qu'il a installés et à quoi ils servent.")
        await send_safe_message(update, context, format_as_html(response))
    elif data == "cmd:setup_user":
        try: await query.edit_message_text(text="Comment souhaites-tu que je t'appelle ? Écris-moi simplement ton prénom.", parse_mode=constants.ParseMode.HTML)
        except Exception: pass
        
    if pending_signal.exists():
        os.rename(pending_signal, config.ROOT_DIR / "restart.signal")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if ALLOWED_USER_ID and str(user.id) != ALLOWED_USER_ID: return
    text = update.message.text
    if not text: return
    
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.effective_chat.id, context, stop_typing))
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, brain.process_message, text)
        stop_typing.set()
        await typing_task
        
        await send_safe_message(update, context, format_as_html(response))
        
        pending_signal = config.ROOT_DIR / "pending_restart.signal"
        if pending_signal.exists():
            os.rename(pending_signal, config.ROOT_DIR / "restart.signal")
    except Exception as e:
        stop_typing.set()
        await typing_task
        await update.message.reply_text(f"❌ <b>Erreur Système</b> : {e}", parse_mode=constants.ParseMode.HTML)

async def proactive_reflection_job(context: ContextTypes.DEFAULT_TYPE):
    if not ALLOWED_USER_ID: return
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, brain.self_reflect)
    if result != "NONE" and not result.startswith("[ERREUR"):
        # On utilise une simulation d'Update pour send_safe_message
        class FakeUpdate:
            def __init__(self):
                self.message = None
                self.callback_query = None
                self.effective_chat = type('obj', (object,), {'id': ALLOWED_USER_ID})
        fake_update = FakeUpdate()
        await send_safe_message(fake_update, context, format_as_html(result))

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
