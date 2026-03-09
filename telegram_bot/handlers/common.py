"""Shared helpers used by all handlers."""
from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from keyboards.menus import main_menu, back_to_main


def get_token(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    return context.user_data.get("token")


def get_user(context: ContextTypes.DEFAULT_TYPE) -> dict | None:
    return context.user_data.get("user")


def is_admin(context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = get_user(context)
    return user is not None and user.get("role") == "admin"


def set_waiting(context: ContextTypes.DEFAULT_TYPE, state: str, **extra) -> None:
    """Mark that the next text message from the user has a specific purpose."""
    context.user_data["waiting_for"] = state
    for k, v in extra.items():
        context.user_data[k] = v


def clear_waiting(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    return context.user_data.pop("waiting_for", None)


async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = "Main Menu") -> None:
    admin = is_admin(context)
    kb = main_menu(is_admin=admin)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb)
    else:
        await update.effective_message.reply_text(text, reply_markup=kb)


async def reply(update: Update, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await update.effective_message.reply_text(text, reply_markup=markup, parse_mode="HTML")


async def send_new(update: Update, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    """Always send a NEW message (never edit)."""
    await update.effective_message.reply_text(text, reply_markup=markup, parse_mode="HTML")


def fmt_bool(v: bool) -> str:
    return "🟢 Active" if v else "🔴 Inactive"
