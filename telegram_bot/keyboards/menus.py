"""
Central place for every InlineKeyboardMarkup used in the bot.
Callback data format: "section:action:id"  (colon-separated, max 64 bytes)
"""
from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup


# ─── Main menu ────────────────────────────────────────────────────────────────

def main_menu(is_admin: bool = False) -> Markup:
    rows = [
        [Btn("📅  Events", callback_data="events:list")],
        [Btn("📊  Analytics Overview", callback_data="analytics:overview")],
        [Btn("👤  My Account", callback_data="account:me")],
    ]
    if is_admin:
        rows.append([Btn("🔑  Admin Panel", callback_data="admin:menu")])
    return Markup(rows)


# ─── Events ───────────────────────────────────────────────────────────────────

def events_list(events: list) -> Markup:
    rows = []
    for ev in events:
        status = "🟢" if ev["is_active"] else "🔴"
        label = f"{status} {ev['name']}  ({ev['total_scans']} scans)"
        rows.append([Btn(label, callback_data=f"events:open:{ev['id']}")])
    rows.append([Btn("➕  Create Event", callback_data="events:create")])
    rows.append([Btn("◀️  Main Menu", callback_data="main:menu")])
    return Markup(rows)


def event_detail(event_id: str, is_active: bool) -> Markup:
    toggle_label = "🔴 Deactivate" if is_active else "🟢 Activate"
    return Markup([
        [Btn("📋  QR Codes", callback_data=f"qr:list:{event_id}")],
        [Btn("📊  Analytics", callback_data=f"analytics:event:{event_id}")],
        [Btn("✏️  Edit Name", callback_data=f"events:editname:{event_id}"),
         Btn(toggle_label, callback_data=f"events:toggle:{event_id}")],
        [Btn("🗑️  Delete Event", callback_data=f"events:delete:{event_id}")],
        [Btn("◀️  Events List", callback_data="events:list")],
    ])


def confirm_delete(section: str, entity_id: str, back_cb: str) -> Markup:
    return Markup([
        [Btn("✅ Yes, delete", callback_data=f"{section}:confirmdelete:{entity_id}"),
         Btn("❌ Cancel", callback_data=back_cb)],
    ])


# ─── QR Codes ─────────────────────────────────────────────────────────────────

def qr_list(qrs: list, event_id: str) -> Markup:
    rows = []
    for qr in qrs:
        status = "🟢" if qr["is_active"] else "🔴"
        label = f"{status} {qr['label']}  ({qr['scan_count']} scans)"
        rows.append([Btn(label, callback_data=f"qr:open:{qr['id']}")])
    rows.append([Btn("➕  Add QR Code", callback_data=f"qr:create:{event_id}")])
    rows.append([Btn("◀️  Back to Event", callback_data=f"events:open:{event_id}")])
    return Markup(rows)


def qr_detail(qr: dict, event_id: str) -> Markup:
    toggle_label = "🔴 Deactivate" if qr["is_active"] else "🟢 Activate"
    return Markup([
        [Btn("✏️  Edit Label", callback_data=f"qr:editlabel:{qr['id']}"),
         Btn("🔗  Edit URL", callback_data=f"qr:editurl:{qr['id']}")],
        [Btn(toggle_label, callback_data=f"qr:toggle:{qr['id']}"),
         Btn("📥  Download QR", callback_data=f"qr:download:{qr['id']}")],
        [Btn("🗑️  Delete", callback_data=f"qr:delete:{qr['id']}")],
        [Btn("◀️  Back to QR List", callback_data=f"qr:list:{event_id}")],
    ])


# ─── Analytics ────────────────────────────────────────────────────────────────

def analytics_period(event_id: str) -> Markup:
    return Markup([
        [Btn("7 days", callback_data=f"analytics:period:{event_id}:7"),
         Btn("30 days", callback_data=f"analytics:period:{event_id}:30"),
         Btn("90 days", callback_data=f"analytics:period:{event_id}:90")],
        [Btn("◀️  Back to Event", callback_data=f"events:open:{event_id}")],
    ])


def back_to_main() -> Markup:
    return Markup([[Btn("◀️  Main Menu", callback_data="main:menu")]])


def back_to_events() -> Markup:
    return Markup([[Btn("◀️  Events", callback_data="events:list")]])


# ─── Account ──────────────────────────────────────────────────────────────────

def account_menu() -> Markup:
    return Markup([
        [Btn("🔗  Re-link Telegram Account", callback_data="account:relink")],
        [Btn("◀️  Main Menu", callback_data="main:menu")],
    ])


# ─── Admin ────────────────────────────────────────────────────────────────────

def admin_menu() -> Markup:
    return Markup([
        [Btn("👥  List Users", callback_data="admin:listusers")],
        [Btn("➕  Create User", callback_data="admin:createuser")],
        [Btn("◀️  Main Menu", callback_data="main:menu")],
    ])


def admin_user_detail(user: dict) -> Markup:
    toggle_label = "🔴 Deactivate" if user["is_active"] else "🟢 Activate"
    return Markup([
        [Btn(toggle_label, callback_data=f"admin:toggleuser:{user['id']}")],
        [Btn("🗑️  Delete User", callback_data=f"admin:deleteuser:{user['id']}")],
        [Btn("◀️  User List", callback_data="admin:listusers")],
    ])
