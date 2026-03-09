"""Analytics callbacks — text-based stats display."""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from services import api_client as api
from services.api_client import APIError
from keyboards import menus
from handlers.common import get_token, reply, get_user


async def cb_overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = get_token(context)
    try:
        data = await api.get_overview(token)
    except APIError as e:
        await reply(update, f"❌ {e}", menus.back_to_main())
        return

    text = (
        "📊 <b>Analytics Overview</b>\n"
        "─────────────────────\n"
        f"📅  Events:            <b>{data['total_events']}</b>\n"
        f"🔷  QR Codes:          <b>{data['total_qr_codes']}</b>\n"
        f"📈  Scans (30 days):   <b>{data['total_scans_30d']}</b>\n"
        f"🔢  Total Scans:       <b>{data['total_scans_all']}</b>\n"
    )
    await reply(update, text, menus.back_to_main())


async def cb_event_choose_period(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str):
    context.user_data["analytics_event_id"] = event_id
    await reply(update, "📊 Choose the time period:", menus.analytics_period(event_id))


async def cb_event_period(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: str, days: int):
    token = get_token(context)
    try:
        data = await api.get_event_analytics(token, event_id, days)
    except APIError as e:
        await reply(update, f"❌ {e}", menus.back_to_main())
        return

    # ── Header ────────────────────────────────────────────────────────────────
    text = (
        f"📊 <b>{data['event_name']}</b>  –  last {days} days\n"
        f"─────────────────────────────\n"
        f"Total scans: <b>{data['total_scans']}</b>\n\n"
    )

    # ── QR breakdown ──────────────────────────────────────────────────────────
    if data["qr_breakdown"]:
        text += "🔷 <b>QR Code Performance</b>\n"
        for i, qr in enumerate(data["qr_breakdown"], 1):
            bar = _mini_bar(qr["scan_count"], data["total_scans"])
            status = "🟢" if qr["is_active"] else "🔴"
            text += f"  {i}. {status} <b>{qr['label']}</b>  {bar}  <b>{qr['scan_count']}</b>\n"
        text += "\n"

    # ── Device breakdown ──────────────────────────────────────────────────────
    if data["device_breakdown"]:
        text += "📱 <b>Devices</b>\n"
        for d in data["device_breakdown"]:
            bar = _mini_bar(d["count"], data["total_scans"])
            text += f"  • {d['device_type'].capitalize()}  {bar}  {d['count']}\n"
        text += "\n"

    # ── Top browsers ──────────────────────────────────────────────────────────
    if data["top_browsers"]:
        text += "🌐 <b>Top Browsers</b>\n"
        for b in data["top_browsers"][:5]:
            text += f"  • {b['browser']}  –  {b['count']}\n"

    await reply(update, text, menus.analytics_period(event_id))


def _mini_bar(count: int, total: int, width: int = 8) -> str:
    if total == 0:
        return "░" * width
    filled = round((count / total) * width)
    return "█" * filled + "░" * (width - filled)
