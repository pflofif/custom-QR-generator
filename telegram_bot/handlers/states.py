"""Conversation states (used across all handlers)."""

# ─── Login flow ───────────────────────────────────────────────────────────────
LOGIN_EMAIL    = "login_email"
LOGIN_PASSWORD = "login_password"

# ─── Event forms ──────────────────────────────────────────────────────────────
CREATE_EVENT_NAME = "create_event_name"
CREATE_EVENT_DESC = "create_event_desc"
EDIT_EVENT_NAME   = "edit_event_name"

# ─── QR forms ─────────────────────────────────────────────────────────────────
CREATE_QR_LABEL = "create_qr_label"
CREATE_QR_URL   = "create_qr_url"
EDIT_QR_LABEL   = "edit_qr_label"
EDIT_QR_URL     = "edit_qr_url"

# ─── Admin forms ──────────────────────────────────────────────────────────────
ADMIN_USER_USERNAME    = "admin_user_username"
ADMIN_USER_EMAIL       = "admin_user_email"
ADMIN_USER_PASSWORD    = "admin_user_password"
ADMIN_USER_TG_USERNAME = "admin_user_tg_username"
ADMIN_USER_ROLE        = "admin_user_role"
