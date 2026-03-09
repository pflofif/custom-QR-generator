from datetime import datetime, timedelta
from collections import defaultdict
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database import get_db
from app.auth import get_current_user
from app.schemas import EventAnalytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/events/{event_id}", response_model=EventAnalytics)
async def event_analytics(
    event_id: str,
    days: int = Query(default=30, ge=1, le=365),
    current_user=Depends(get_current_user),
):
    db = get_db()
    event = await db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(404, "Event not found")
    if current_user["role"] != "admin" and str(event["owner_id"]) != current_user["id"]:
        raise HTTPException(403, "Access denied")

    since = datetime.utcnow() - timedelta(days=days)
    event_oid = event["_id"]

    # ── gather all scan logs for this event ──────────────────────────────────
    logs = await db.scan_logs.find(
        {"event_id": event_oid, "scanned_at": {"$gte": since}}
    ).to_list(length=None)

    total_scans = len(logs)

    # ── per-QR breakdown ─────────────────────────────────────────────────────
    qr_scan_map: dict = defaultdict(int)
    for log in logs:
        qr_scan_map[str(log["qr_id"])] += 1

    qr_breakdown = []
    async for qr in db.qr_codes.find({"event_id": event_oid}):
        qr_breakdown.append({
            "qr_id": str(qr["_id"]),
            "label": qr["label"],
            "short_id": qr["short_id"],
            "scan_count": qr_scan_map.get(str(qr["_id"]), 0),
            "is_active": qr.get("is_active", True),
        })
    qr_breakdown.sort(key=lambda x: x["scan_count"], reverse=True)

    # ── time series (daily buckets) ───────────────────────────────────────────
    daily: dict = defaultdict(int)
    for log in logs:
        day = log["scanned_at"].strftime("%Y-%m-%d")
        daily[day] += 1

    # Fill every day in the range (even zero-scan days)
    time_series = []
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        time_series.append({"date": d, "count": daily.get(d, 0)})

    # ── device breakdown ──────────────────────────────────────────────────────
    device_map: dict = defaultdict(int)
    for log in logs:
        device_map[log.get("device_type", "unknown")] += 1
    device_breakdown = [{"device_type": k, "count": v} for k, v in device_map.items()]

    # ── top browsers ─────────────────────────────────────────────────────────
    browser_map: dict = defaultdict(int)
    for log in logs:
        browser_map[log.get("browser", "unknown")] += 1
    top_browsers = sorted(
        [{"browser": k, "count": v} for k, v in browser_map.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    return EventAnalytics(
        event_id=event_id,
        event_name=event["name"],
        total_scans=total_scans,
        qr_breakdown=qr_breakdown,
        time_series=time_series,
        device_breakdown=device_breakdown,
        top_browsers=top_browsers,
    )


@router.get("/overview")
async def overview_analytics(current_user=Depends(get_current_user)):
    """High-level numbers for the dashboard overview card."""
    db = get_db()
    query = {} if current_user["role"] == "admin" else {"owner_id": ObjectId(current_user["id"])}

    total_events = await db.events.count_documents(query)
    total_qrs = await db.qr_codes.count_documents(
        {} if current_user["role"] == "admin" else {"owner_id": ObjectId(current_user["id"])}
    )

    # Scans in the last 30 days
    since = datetime.utcnow() - timedelta(days=30)
    scan_query = {"scanned_at": {"$gte": since}}
    if current_user["role"] != "admin":
        scan_query["owner_id"] = ObjectId(current_user["id"])

    total_scans_30d = await db.scan_logs.count_documents(scan_query)
    total_scans_all = await db.scan_logs.count_documents(
        {} if current_user["role"] == "admin" else {"owner_id": ObjectId(current_user["id"])}
    )

    return {
        "total_events": total_events,
        "total_qr_codes": total_qrs,
        "total_scans_30d": total_scans_30d,
        "total_scans_all": total_scans_all,
    }
