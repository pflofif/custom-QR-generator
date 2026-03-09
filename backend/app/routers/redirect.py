from datetime import datetime
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import RedirectResponse
from bson import ObjectId
from app.database import get_db

router = APIRouter(tags=["redirect"])


async def _log_scan(db, qr_doc: dict, request: Request):
    """Background task: parse UA and persist a scan log."""
    try:
        ua_string = request.headers.get("user-agent", "")
        referer = request.headers.get("referer", "")
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        ip = ip.split(",")[0].strip()

        device_type = "unknown"
        os_name = "unknown"
        browser_name = "unknown"

        try:
            from user_agents import parse as ua_parse
            ua = ua_parse(ua_string)
            if ua.is_mobile:
                device_type = "mobile"
            elif ua.is_tablet:
                device_type = "tablet"
            elif ua.is_pc:
                device_type = "desktop"
            os_name = ua.os.family or "unknown"
            browser_name = ua.browser.family or "unknown"
        except Exception:
            pass

        log = {
            "short_id": qr_doc["short_id"],
            "qr_id": qr_doc["_id"],
            "event_id": qr_doc["event_id"],
            "owner_id": qr_doc["owner_id"],
            "ip_address": ip,
            "user_agent": ua_string[:500],
            "referer": referer[:500] if referer else None,
            "device_type": device_type,
            "os": os_name,
            "browser": browser_name,
            "scanned_at": datetime.utcnow(),
            "telegram_user_id": None,  # reserved for Telegram Bot integration
        }
        await db.scan_logs.insert_one(log)
    except Exception as e:
        print(f"[scan_log error] {e}")


@router.get("/r/{short_id}")
async def redirect(short_id: str, request: Request, background_tasks: BackgroundTasks):
    db = get_db()
    qr_doc = await db.qr_codes.find_one({"short_id": short_id})
    if not qr_doc:
        raise HTTPException(status_code=404, detail="QR code not found or has been deleted.")
    if not qr_doc.get("is_active", True):
        raise HTTPException(status_code=410, detail="This QR code has been deactivated.")

    # Fire-and-forget scan logging – does NOT block the redirect
    background_tasks.add_task(_log_scan, db, qr_doc, request)

    return RedirectResponse(url=qr_doc["target_url"], status_code=302)
