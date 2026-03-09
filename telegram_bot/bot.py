"""
Main entry point for the QR Platform Telegram Bot.
Registers all handlers and starts polling.
"""
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from config import BOT_TOKEN
from handlers.auth import build_login_conversation, cmd_cancel, cmd_logout
from handlers.dispatcher import handle_callback
from handlers.common import get_token, send_main_menu, is_admin
from handlers.states import (
    CREATE_EVENT_NAME, CREATE_EVENT_DESC, EDIT_EVENT_NAME,
    CREATE_QR_LABEL, CREATE_QR_URL, EDIT_QR_LABEL, EDIT_QR_URL,
    ADMIN_USER_USERNAME, ADMIN_USER_EMAIL, ADMIN_USER_PASSWORD,
    ADMIN_USER_TG_USERNAME, ADMIN_USER_ROLE,
)
from handlers import events as ev_h, qrcodes as qr_h, admin as adm_h

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── Text input router ────────────────────────────────────────────────────────

_TEXT_ROUTES = {
    CREATE_EVENT_NAME:     ev_h.text_create_name,
    CREATE_EVENT_DESC:     ev_h.text_create_desc,
    EDIT_EVENT_NAME:       ev_h.text_edit_name,
    CREATE_QR_LABEL:       qr_h.text_create_label,
    CREATE_QR_URL:         qr_h.text_create_url,
    EDIT_QR_LABEL:         qr_h.text_edit_label,
    EDIT_QR_URL:           qr_h.text_edit_url,
    ADMIN_USER_USERNAME:   adm_h.text_username,
    ADMIN_USER_EMAIL:      adm_h.text_email,
    ADMIN_USER_PASSWORD:   adm_h.text_password,
    ADMIN_USER_TG_USERNAME:adm_h.text_tg_username,
}


async def handle_text_input(update: Update, context):
    """Dispatch free-text messages to the handler that is currently waiting."""
    if not get_token(context):
        await update.message.reply_text("🔒 Please send /start to log in first.")
        return

    waiting = context.user_data.get("waiting_for")
    handler = _TEXT_ROUTES.get(waiting)
    if handler:
        await handler(update, context)
    else:
        # Default: show main menu when no form is active
        await send_main_menu(update, context, "Use the menu below 👇")


# ─── /help command ────────────────────────────────────────────────────────────

async def cmd_help(update: Update, context):
    help_text = (
        "🤖 <b>QR Platform Bot</b>\n\n"
        "<b>Commands:</b>\n"
        "/start  — log in / show main menu\n"
        "/logout — log out\n"
        "/cancel — cancel current action\n"
        "/help   — this message\n\n"
        "<b>Navigation:</b>\n"
        "Use the inline buttons to manage events, QR codes and analytics.\n"
        "Admins also have access to the Users panel."
    )
    await update.message.reply_html(help_text)


# ─── Application factory ──────────────────────────────────────────────────────

def build_app() -> Application:
    persistence = PicklePersistence(filepath=Path("bot_data") / "sessions.pkl")
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    # 1. Login conversation (must be registered first — handles /start)
    app.add_handler(build_login_conversation())

    # 2. Callback queries (all inline-keyboard button clicks)
    app.add_handler(CallbackQueryHandler(handle_callback))

    # 3. Free-text messages (form inputs)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    # 4. Utility commands
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("logout", cmd_logout))
    app.add_handler(CommandHandler("help",   cmd_help))

    return app


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Path("bot_data").mkdir(exist_ok=True)
    logger.info("Starting QR Platform Bot …")
    build_app().run_polling(allowed_updates=Update.ALL_TYPES)
