"""Admin-only callbacks and text-input handlers for user management."""
from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from services import api_client as api
from services.api_client import APIError
from keyboards import menus
from handlers.common import get_token, set_waiting, clear_waiting, reply, fmt_bool
from handlers import states


# ─── Menu ─────────────────────────────────────────────────────────────────────

async def cb_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, "🔑 <b>Admin Panel</b>\n\nManage users and platform settings.", menus.admin_menu())


# ─── List users ───────────────────────────────────────────────────────────────

async def cb_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = get_token(context)
    try:
        users = await api.admin_list_users(token)
    except APIError as e:
        await reply(update, f"❌ {e}", menus.back_to_main())
        return

    if not users:
        await reply(update, "👥 No users found.", menus.admin_menu())
        return

    from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup
    rows = []
    for u in users:
        status = "🟢" if u["is_active"] else "🔴"
        role_icon = "🔑" if u["role"] == "admin" else "👤"
        tg = f"  @{u['telegram_username']}" if u.get("telegram_username") else ""
        rows.append([Btn(
            f"{status} {role_icon} {u['username']}{tg}",
            callback_data=f"admin:openuser:{u['id']}",
        )])
    rows.append([Btn("◀️  Admin Menu", callback_data="admin:menu")])
    await reply(update, f"👥 <b>Users</b>  ({len(users)} total)", Markup(rows))


async def cb_open_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
    token = get_token(context)
    try:
        users = await api.admin_list_users(token)
    except APIError as e:
        await reply(update, f"❌ {e}")
        return
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        await reply(update, "❌ User not found.", menus.admin_menu())
        return
    context.user_data["admin_selected_user_id"] = user_id
    tg_info = ""
    if user.get("telegram_username"):
        tg_info += f"\nTelegram: @{user['telegram_username']}"
    if user.get("telegram_chat_id"):
        tg_info += f"  (chat linked ✅)"
    text = (
        f"👤 <b>{user['username']}</b>\n"
        f"Email: {user['email']}\n"
        f"Role: {user['role']}\n"
        f"Status: {fmt_bool(user['is_active'])}"
        f"{tg_info}"
    )
    await reply(update, text, menus.admin_user_detail(user))


async def cb_toggle_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
    token = get_token(context)
    try:
        users = await api.admin_list_users(token)
        user = next((u for u in users if u["id"] == user_id), None)
        if not user:
            await reply(update, "❌ User not found.")
            return
        await api.admin_update_user(token, user_id, is_active=not user["is_active"])
    except APIError as e:
        await reply(update, f"❌ {e}")
        return
    await cb_open_user(update, context, user_id)


async def cb_delete_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
    await reply(
        update,
        "⚠️ Permanently delete this user?",
        menus.confirm_delete("admin", user_id, f"admin:openuser:{user_id}"),
    )


async def cb_confirm_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
    token = get_token(context)
    try:
        await api.admin_delete_user(token, user_id)
    except APIError as e:
        await reply(update, f"❌ {e}")
        return
    await reply(update, "🗑️ User deleted.", menus.admin_menu())


# ─── Create user ──────────────────────────────────────────────────────────────

async def cb_create_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("_new_user", None)
    set_waiting(context, states.ADMIN_USER_USERNAME)
    await reply(update, "➕ <b>Create New User</b>\n\nStep 1/5 — Enter <b>username</b>:\n\n/cancel to abort")


async def text_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_waiting(context)
    val = update.message.text.strip()
    context.user_data.setdefault("_new_user", {})["username"] = val
    set_waiting(context, states.ADMIN_USER_EMAIL)
    await update.message.reply_text(
        f"Username: <b>{val}</b>\n\nStep 2/5 — Enter <b>email</b>:", parse_mode="HTML"
    )


async def text_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_waiting(context)
    val = update.message.text.strip()
    if "@" not in val:
        set_waiting(context, states.ADMIN_USER_EMAIL)
        await update.message.reply_text("❌ Invalid email. Try again:")
        return
    context.user_data.setdefault("_new_user", {})["email"] = val
    set_waiting(context, states.ADMIN_USER_PASSWORD)
    await update.message.reply_text(
        f"Email: <b>{val}</b>\n\nStep 3/5 — Enter <b>password</b> (min 6 chars):", parse_mode="HTML"
    )


async def text_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_waiting(context)
    val = update.message.text.strip()
    try:
        await update.message.delete()
    except Exception:
        pass
    if len(val) < 6:
        set_waiting(context, states.ADMIN_USER_PASSWORD)
        await update.effective_chat.send_message("❌ Password too short (min 6 chars). Try again:")
        return
    context.user_data.setdefault("_new_user", {})["password"] = val
    set_waiting(context, states.ADMIN_USER_TG_USERNAME)
    await update.effective_chat.send_message(
        "Step 4/5 — Enter Telegram <b>username</b> to link this account\n"
        "(e.g. <code>john_doe</code> without @).\n\n"
        "Send <code>-</code> to skip.",
        parse_mode="HTML",
    )


async def text_tg_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_waiting(context)
    val = update.message.text.strip().lstrip("@")
    if val != "-":
        context.user_data.setdefault("_new_user", {})["telegram_username"] = val
    set_waiting(context, states.ADMIN_USER_ROLE)
    from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup
    kb = Markup([[
        Btn("👤 User", callback_data="admin:setrole:user"),
        Btn("🔑 Admin", callback_data="admin:setrole:admin"),
    ]])
    await update.message.reply_text(
        "Step 5/5 — Select <b>role</b>:", parse_mode="HTML", reply_markup=kb
    )


async def cb_set_role(update: Update, context: ContextTypes.DEFAULT_TYPE, role: str):
    clear_waiting(context)
    new_user = context.user_data.pop("_new_user", {})
    new_user["role"] = role
    token = get_token(context)
    try:
        user = await api.admin_create_user(
            token,
            username=new_user["username"],
            email=new_user["email"],
            password=new_user["password"],
            role=role,
            telegram_username=new_user.get("telegram_username"),
        )
    except APIError as e:
        await reply(update, f"❌ Failed to create user: {e}", menus.admin_menu())
        return

    tg = f"\nTelegram: @{user['telegram_username']}" if user.get("telegram_username") else ""
    await reply(
        update,
        f"✅ User <b>{user['username']}</b> created!\n"
        f"Email: {user['email']}\n"
        f"Role: {user['role']}{tg}\n\n"
        f"They can now log in at the web dashboard or via this bot.",
        menus.admin_menu(),
    )
