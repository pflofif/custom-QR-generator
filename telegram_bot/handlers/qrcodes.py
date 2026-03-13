"""Callbacks and text-input handlers for QR Codes."""
from __future__ import annotations
import io
from telegram import Update
from telegram.ext import ContextTypes
from services import api_client as api
from services.api_client import APIError
from keyboards import menus
from handlers.common import (
    get_token, set_waiting, clear_waiting, reply, fmt_bool,
)
from handlers import states


def _find_event_id_for_qr(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    return context.user_data.get("current_event_id")


# ─── Callbacks ────────────────────────────────────────────────────────────────

async def cb_list(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str):
    token = get_token(context)
    context.user_data["current_event_id"] = event_id
    try:
        qrs = await api.list_qrcodes(token, event_id)
    except APIError as e:
        await reply(update, f"❌ {e}", menus.back_to_events())
        return
    if not qrs:
        from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup
        kb = Markup([
            [Btn("➕  Add QR Code", callback_data=f"qr:create:{event_id}")],
            [Btn("◀️  Back", callback_data=f"events:open:{event_id}")],
        ])
        await reply(update, "📭 No QR codes yet.\n\nAdd your first!", kb)
        return
    text = f"📋 <b>QR Codes</b>  ({len(qrs)} total)\n\nTap a QR code to manage it:"
    await reply(update, text, menus.qr_list(qrs, event_id))


async def cb_open(update: Update, context: ContextTypes.DEFAULT_TYPE, qr_id: str):
    token = get_token(context)
    event_id = _find_event_id_for_qr(context)
    # Find the QR in the list (need event_id)
    try:
        qrs = await api.list_qrcodes(token, event_id)
    except APIError as e:
        await reply(update, f"❌ {e}")
        return
    qr = next((q for q in qrs if q["id"] == qr_id), None)
    if not qr:
        await reply(update, "❌ QR code not found.", menus.back_to_events())
        return
    context.user_data["current_qr_id"] = qr_id
    context.user_data["current_qr_event_id"] = event_id
    text = (
        f"🔷 <b>{qr['label']}</b>\n"
        f"Status: {fmt_bool(qr['is_active'])}\n"
        f"Scans: <b>{qr['scan_count']}</b>\n\n"
        f"🔗 Proxy URL:\n<code>{qr['proxy_url']}</code>\n\n"
        f"🎯 Destination:\n<code>{qr['target_url']}</code>"
    )
    await reply(update, text, menus.qr_detail(qr, event_id))


async def cb_create_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str):
    context.user_data["creating_qr_event_id"] = event_id
    context.user_data["current_event_id"] = event_id
    set_waiting(context, states.CREATE_QR_LABEL)
    await reply(update, "🏷️ Enter a <b>label</b> for this QR code:\n(e.g. <i>Entrance Poster</i>)\n\n/cancel to abort")


async def cb_editlabel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, qr_id: str):
    set_waiting(context, states.EDIT_QR_LABEL, editing_qr_id=qr_id)
    await reply(update, "✏️ Enter the <b>new label</b>:\n\n/cancel to abort")


async def cb_editurl_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, qr_id: str):
    set_waiting(context, states.EDIT_QR_URL, editing_qr_id=qr_id)
    await reply(update, "🔗 Enter the <b>new destination URL</b>:\n\n/cancel to abort")


async def cb_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, qr_id: str):
    token = get_token(context)
    event_id = context.user_data.get("current_qr_event_id") or _find_event_id_for_qr(context)
    try:
        qrs = await api.list_qrcodes(token, event_id)
        qr = next((q for q in qrs if q["id"] == qr_id), None)
        if not qr:
            await reply(update, "❌ QR not found.")
            return
        await api.update_qrcode(token, event_id, qr_id, is_active=not qr["is_active"])
    except APIError as e:
        await reply(update, f"❌ {e}")
        return
    await cb_open(update, context, qr_id)


async def cb_delete_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, qr_id: str):
    event_id = context.user_data.get("current_qr_event_id") or _find_event_id_for_qr(context)
    await reply(
        update,
        "⚠️ Delete this QR code?\n\nAll its scan history will also be removed!",
        menus.confirm_delete("qr", qr_id, f"qr:open:{qr_id}"),
    )


async def cb_confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, qr_id: str):
    token = get_token(context)
    event_id = context.user_data.get("current_qr_event_id") or _find_event_id_for_qr(context)
    try:
        await api.delete_qrcode(token, event_id, qr_id)
    except APIError as e:
        await reply(update, f"❌ {e}")
        return
    await reply(update, "🗑️ QR code deleted.", menus.back_to_events())


async def cb_download(update: Update, context: ContextTypes.DEFAULT_TYPE, qr_id: str):
    token = get_token(context)
    event_id = context.user_data.get("current_qr_event_id") or _find_event_id_for_qr(context)
    await update.callback_query.answer("⏳ Generating QR image…")
    try:
        img_bytes = await api.get_qr_image(token, event_id, qr_id)
    except APIError as e:
        await update.effective_chat.send_message(f"❌ {e}")
        return
    is_gif = img_bytes[:3] == b"GIF"
    ext = "gif" if is_gif else "png"
    caption = "📥 Here is your QR code!" + (" (animated GIF — send as a file to keep animation)" if is_gif else "")
    await update.effective_chat.send_document(
        document=io.BytesIO(img_bytes),
        filename=f"qr_{qr_id}.{ext}",
        caption=caption,
    )


# ─── Text input ───────────────────────────────────────────────────────────────

async def text_create_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_waiting(context)
    label = update.message.text.strip()
    context.user_data["_new_qr_label"] = label
    set_waiting(context, states.CREATE_QR_URL)
    await update.message.reply_text(
        f"Label: <b>{label}</b>\n\n🔗 Now enter the <b>destination URL</b>:\n(e.g. <i>https://example.com/register</i>)\n\n/cancel to abort",
        parse_mode="HTML",
    )


async def text_create_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_waiting(context)
    url = update.message.text.strip()
    if not url.startswith("http"):
        url = "https://" + url
    label = context.user_data.pop("_new_qr_label", "QR")
    event_id = context.user_data.get("creating_qr_event_id") or _find_event_id_for_qr(context)
    token = get_token(context)
    try:
        qr = await api.create_qrcode(token, event_id, label, url)
    except APIError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    context.user_data["current_qr_id"] = qr["id"]
    context.user_data["current_qr_event_id"] = event_id
    await update.message.reply_text(
        f"✅ QR code <b>{qr['label']}</b> created!\n\n"
        f"🔗 Proxy URL:\n<code>{qr['proxy_url']}</code>",
        parse_mode="HTML",
        reply_markup=menus.qr_detail(qr, event_id),
    )


async def text_edit_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_waiting(context)
    new_label = update.message.text.strip()
    qr_id = context.user_data.pop("editing_qr_id", None)
    event_id = context.user_data.get("current_qr_event_id") or _find_event_id_for_qr(context)
    token = get_token(context)
    try:
        await api.update_qrcode(token, event_id, qr_id, label=new_label)
    except APIError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    await update.message.reply_text(f"✅ Label updated to <b>{new_label}</b>", parse_mode="HTML")


async def text_edit_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_waiting(context)
    new_url = update.message.text.strip()
    if not new_url.startswith("http"):
        new_url = "https://" + new_url
    qr_id = context.user_data.pop("editing_qr_id", None)
    event_id = context.user_data.get("current_qr_event_id") or _find_event_id_for_qr(context)
    token = get_token(context)
    try:
        qr = await api.update_qrcode(token, event_id, qr_id, target_url=new_url)
    except APIError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    await update.message.reply_text(
        f"✅ Destination URL updated!\n<code>{new_url}</code>\n\n"
        f"All existing printed QR codes now point here automatically.",
        parse_mode="HTML",
        reply_markup=menus.qr_detail(qr, event_id),
    )
