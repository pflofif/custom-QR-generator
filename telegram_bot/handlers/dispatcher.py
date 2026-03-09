"""
Callback query dispatcher.
Parses callback_data in the format "section:action[:id[:extra]]"
and routes to the appropriate handler function.
"""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from handlers.common import get_token, is_admin, send_main_menu
from handlers import events as ev_h, qrcodes as qr_h, analytics as an_h, admin as adm_h


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Always verify the user is logged in
    if not get_token(context):
        await query.edit_message_text(
            "🔒 Session expired. Send /start to log in again."
        )
        return

    data = query.data or ""
    parts = data.split(":")
    section = parts[0] if len(parts) > 0 else ""
    action  = parts[1] if len(parts) > 1 else ""
    p2      = parts[2] if len(parts) > 2 else ""
    p3      = parts[3] if len(parts) > 3 else ""

    # ── Main menu ─────────────────────────────────────────────────────────────
    if section == "main":
        await send_main_menu(update, context, "🏠 Main Menu")

    # ── Events ────────────────────────────────────────────────────────────────
    elif section == "events":
        if action == "list":              await ev_h.cb_list(update, context)
        elif action == "open":            await ev_h.cb_open(update, context, p2)
        elif action == "create":          await ev_h.cb_create_prompt(update, context)
        elif action == "editname":        await ev_h.cb_editname_prompt(update, context, p2)
        elif action == "toggle":          await ev_h.cb_toggle(update, context, p2)
        elif action == "delete":          await ev_h.cb_delete_prompt(update, context, p2)
        elif action == "confirmdelete":   await ev_h.cb_confirm_delete(update, context, p2)

    # ── QR Codes ──────────────────────────────────────────────────────────────
    elif section == "qr":
        if action == "list":              await qr_h.cb_list(update, context, p2)
        elif action == "open":            await qr_h.cb_open(update, context, p2)
        elif action == "create":          await qr_h.cb_create_prompt(update, context, p2)
        elif action == "editlabel":       await qr_h.cb_editlabel_prompt(update, context, p2)
        elif action == "editurl":         await qr_h.cb_editurl_prompt(update, context, p2)
        elif action == "toggle":          await qr_h.cb_toggle(update, context, p2)
        elif action == "delete":          await qr_h.cb_delete_prompt(update, context, p2)
        elif action == "confirmdelete":   await qr_h.cb_confirm_delete(update, context, p2)
        elif action == "download":        await qr_h.cb_download(update, context, p2)

    # ── Analytics ─────────────────────────────────────────────────────────────
    elif section == "analytics":
        if action == "overview":          await an_h.cb_overview(update, context)
        elif action == "event":           await an_h.cb_event_choose_period(update, context, p2)
        elif action == "period":          await an_h.cb_event_period(update, context, p2, int(p3 or 30))

    # ── Account ───────────────────────────────────────────────────────────────
    elif section == "account":
        if action == "me":                await _account_me(update, context)
        elif action == "relink":          await _relink(update, context)

    # ── Admin ─────────────────────────────────────────────────────────────────
    elif section == "admin":
        if not is_admin(context):
            await query.edit_message_text("⛔ Admin access required.")
            return
        if action == "menu":              await adm_h.cb_menu(update, context)
        elif action == "listusers":       await adm_h.cb_list_users(update, context)
        elif action == "openuser":        await adm_h.cb_open_user(update, context, p2)
        elif action == "toggleuser":      await adm_h.cb_toggle_user(update, context, p2)
        elif action == "deleteuser":      await adm_h.cb_delete_user_prompt(update, context, p2)
        elif action == "confirmdelete":   await adm_h.cb_confirm_delete_user(update, context, p2)
        elif action == "createuser":      await adm_h.cb_create_user_prompt(update, context)
        elif action == "setrole":         await adm_h.cb_set_role(update, context, p2)


async def _account_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services import api_client as api
    token = get_token(context)
    user = context.user_data.get("user", {})
    tg = f"\nTelegram: @{user.get('telegram_username', '—')}"
    linked = "✅ linked" if user.get("telegram_chat_id") else "❌ not linked"
    text = (
        f"👤 <b>{user.get('username', '—')}</b>\n"
        f"Email: {user.get('email', '—')}\n"
        f"Role: {user.get('role', '—')}\n"
        f"Telegram: {linked}{tg}"
    )
    from keyboards.menus import account_menu
    await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=account_menu())


async def _relink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services import api_client as api
    from services.api_client import APIError
    from keyboards.menus import back_to_main
    token = get_token(context)
    tg_user = update.effective_user
    try:
        updated = await api.link_telegram(token, tg_user.id, tg_user.username)
        context.user_data["user"] = updated
        await update.callback_query.edit_message_text(
            "✅ Telegram account re-linked successfully!",
            reply_markup=back_to_main(),
        )
    except APIError as e:
        await update.callback_query.edit_message_text(f"❌ {e}", reply_markup=back_to_main())
