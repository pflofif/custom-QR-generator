"""
Login flow — ConversationHandler.
Entry point: /start (unauthenticated)  OR  /login
Steps: email → password → link chat_id → show main menu
"""
from __future__ import annotations
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters,
)
from services import api_client as api
from services.api_client import APIError
from handlers.common import send_main_menu
from handlers.states import LOGIN_EMAIL, LOGIN_PASSWORD

_ASK_EMAIL, _ASK_PASSWORD = range(2)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = context.user_data.get("token")
    if token:
        # already logged in
        try:
            user = await api.get_me(token)
            context.user_data["user"] = user
            await send_main_menu(update, context, f"👋 Welcome back, <b>{user['username']}</b>!")
            return ConversationHandler.END
        except APIError:
            context.user_data.clear()

    await update.message.reply_text(
        "👋 <b>Welcome to QR Platform</b>\n\n"
        "This is an internal company tool. Please log in with your credentials.\n\n"
        "📧 Enter your <b>email address</b>:",
        parse_mode="HTML",
    )
    return _ASK_EMAIL


async def _got_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    if "@" not in email:
        await update.message.reply_text("❌ That doesn't look like a valid email. Try again:")
        return _ASK_EMAIL
    context.user_data["_login_email"] = email
    await update.message.reply_text("🔒 Enter your <b>password</b>:", parse_mode="HTML")
    return _ASK_PASSWORD


async def _got_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    email = context.user_data.pop("_login_email", "")
    # Delete the password message for security
    try:
        await update.message.delete()
    except Exception:
        pass

    try:
        data = await api.login(email, password)
    except APIError as e:
        await update.effective_chat.send_message(
            f"❌ Login failed: <b>{e}</b>\n\nSend /start to try again.",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    token = data["access_token"]
    user = data["user"]
    context.user_data["token"] = token
    context.user_data["user"] = user

    # Link Telegram chat_id to backend account
    tg_user = update.effective_user
    try:
        await api.link_telegram(token, tg_user.id, tg_user.username)
    except APIError:
        pass  # non-fatal

    await send_main_menu(
        update, context,
        f"✅ Logged in as <b>{user['username']}</b>  ({user['role']})\n\nWhat would you like to do?"
    )
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("waiting_for", None)
    await update.message.reply_text("❌ Cancelled.")
    if context.user_data.get("token"):
        await send_main_menu(update, context)
    return ConversationHandler.END


async def cmd_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Logged out. Send /start to log in again."
    )


def build_login_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            CommandHandler("login", cmd_start),
        ],
        states={
            _ASK_EMAIL:    [MessageHandler(filters.TEXT & ~filters.COMMAND, _got_email)],
            _ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, _got_password)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        name="login",
        persistent=True,
    )
