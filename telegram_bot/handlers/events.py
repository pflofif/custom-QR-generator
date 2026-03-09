"""Callbacks and text-input handlers for Events."""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from services import api_client as api
from services.api_client import APIError
from keyboards import menus
from handlers.common import (
    get_token, set_waiting, clear_waiting, reply, send_main_menu, fmt_bool,
)
from handlers import states


# ─── Callbacks ────────────────────────────────────────────────────────────────

async def cb_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = get_token(context)
    try:
        events = await api.list_events(token)
    except APIError as e:
        await reply(update, f"❌ {e}", menus.back_to_main())
        return
    if not events:
        from keyboards.menus import Markup, Btn
        kb = Markup([
            [Btn("➕  Create Event", callback_data="events:create")],
            [Btn("◀️  Main Menu", callback_data="main:menu")],
        ])
        await reply(update, "📭 No events yet.\n\nCreate your first!", kb)
        return
    text = f"📅 <b>Your Events</b>  ({len(events)} total)\n\nTap an event to manage it:"
    await reply(update, text, menus.events_list(events))


async def cb_open(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str):
    token = get_token(context)
    try:
        ev = await api.get_event(token, event_id)
    except APIError as e:
        await reply(update, f"❌ {e}", menus.back_to_events())
        return
    context.user_data["current_event_id"] = event_id
    context.user_data["current_event_name"] = ev["name"]
    text = (
        f"📅 <b>{ev['name']}</b>\n"
        f"Status: {fmt_bool(ev['is_active'])}\n"
        f"QR Codes: <b>{ev['qr_count']}</b>\n"
        f"Total Scans: <b>{ev['total_scans']}</b>\n"
    )
    if ev.get("description"):
        text += f"<i>{ev['description']}</i>\n"
    await reply(update, text, menus.event_detail(event_id, ev["is_active"]))


async def cb_create_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_waiting(context, states.CREATE_EVENT_NAME)
    await reply(update, "📝 Enter the <b>event name</b>:\n\n/cancel to abort")


async def cb_editname_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str):
    set_waiting(context, states.EDIT_EVENT_NAME, editing_event_id=event_id)
    await reply(update, "✏️ Enter the <b>new event name</b>:\n\n/cancel to abort")


async def cb_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str):
    token = get_token(context)
    try:
        ev = await api.get_event(token, event_id)
        await api.update_event(token, event_id, is_active=not ev["is_active"])
    except APIError as e:
        await reply(update, f"❌ {e}")
        return
    await cb_open(update, context, event_id)


async def cb_delete_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str):
    name = context.user_data.get("current_event_name", event_id)
    await reply(
        update,
        f"⚠️ Delete event <b>{name}</b>?\n\nThis will also delete all QR codes and scan history!",
        menus.confirm_delete("events", event_id, f"events:open:{event_id}"),
    )


async def cb_confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str):
    token = get_token(context)
    try:
        await api.delete_event(token, event_id)
    except APIError as e:
        await reply(update, f"❌ {e}")
        return
    await reply(update, "🗑️ Event deleted.", menus.back_to_events())


# ─── Text input ───────────────────────────────────────────────────────────────

async def text_create_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_waiting(context)
    name = update.message.text.strip()
    context.user_data["_new_event_name"] = name
    set_waiting(context, states.CREATE_EVENT_DESC)
    await update.message.reply_text(
        f"Got it: <b>{name}</b>\n\n📝 Add a description (or send <code>-</code> to skip):",
        parse_mode="HTML",
    )


async def text_create_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_waiting(context)
    desc = update.message.text.strip()
    if desc == "-":
        desc = ""
    name = context.user_data.pop("_new_event_name", "New Event")
    token = get_token(context)
    try:
        ev = await api.create_event(token, name, desc)
    except APIError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    context.user_data["current_event_id"] = ev["id"]
    context.user_data["current_event_name"] = ev["name"]
    await update.message.reply_text(
        f"✅ Event <b>{ev['name']}</b> created!",
        parse_mode="HTML",
        reply_markup=menus.event_detail(ev["id"], True),
    )


async def text_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_waiting(context)
    new_name = update.message.text.strip()
    event_id = context.user_data.pop("editing_event_id", None)
    token = get_token(context)
    try:
        ev = await api.update_event(token, event_id, name=new_name)
    except APIError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    context.user_data["current_event_name"] = ev["name"]
    await update.message.reply_text(
        f"✅ Event renamed to <b>{ev['name']}</b>",
        parse_mode="HTML",
        reply_markup=menus.event_detail(event_id, ev["is_active"]),
    )
