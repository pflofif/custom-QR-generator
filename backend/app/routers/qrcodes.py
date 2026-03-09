from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import StreamingResponse
import shortuuid
import io
from app.database import get_db
from app.auth import get_current_user
from app.schemas import QRCreateRequest, QRUpdateRequest, QRResponse
from app.qr_generator import generate_qr_base64, generate_qr_bytes
from app.config import settings

router = APIRouter(prefix="/api/events/{event_id}/qrcodes", tags=["qrcodes"])


def _proxy_url(short_id: str) -> str:
    return f"{settings.base_url}/r/{short_id}"


def _map_qr(doc: dict, scan_count: int = 0) -> QRResponse:
    return QRResponse(
        id=str(doc["_id"]),
        short_id=doc["short_id"],
        label=doc["label"],
        target_url=doc["target_url"],
        event_id=str(doc["event_id"]),
        owner_id=str(doc["owner_id"]),
        is_active=doc.get("is_active", True),
        proxy_url=_proxy_url(doc["short_id"]),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        scan_count=scan_count,
    )


async def _assert_event_access(event_id: str, current_user: dict, db):
    doc = await db.events.find_one({"_id": ObjectId(event_id)})
    if not doc:
        raise HTTPException(404, "Event not found")
    if current_user["role"] != "admin" and str(doc["owner_id"]) != current_user["id"]:
        raise HTTPException(403, "Access denied")
    return doc


@router.post("", response_model=QRResponse, status_code=201)
async def create_qrcode(event_id: str, body: QRCreateRequest, current_user=Depends(get_current_user)):
    db = get_db()
    event = await _assert_event_access(event_id, current_user, db)
    short_id = shortuuid.ShortUUID().random(length=8)
    # Ensure uniqueness
    while await db.qr_codes.find_one({"short_id": short_id}):
        short_id = shortuuid.ShortUUID().random(length=8)

    now = datetime.utcnow()
    doc = {
        "short_id": short_id,
        "label": body.label,
        "target_url": body.target_url,
        "event_id": event["_id"],
        "owner_id": ObjectId(current_user["id"]),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.qr_codes.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _map_qr(doc)


@router.get("", response_model=list[QRResponse])
async def list_qrcodes(event_id: str, current_user=Depends(get_current_user)):
    db = get_db()
    event = await _assert_event_access(event_id, current_user, db)
    qrs = []
    async for doc in db.qr_codes.find({"event_id": event["_id"]}).sort("created_at", -1):
        scan_count = await db.scan_logs.count_documents({"qr_id": doc["_id"]})
        qrs.append(_map_qr(doc, scan_count))
    return qrs


@router.get("/{qr_id}", response_model=QRResponse)
async def get_qrcode(event_id: str, qr_id: str, current_user=Depends(get_current_user)):
    db = get_db()
    await _assert_event_access(event_id, current_user, db)
    doc = await db.qr_codes.find_one({"_id": ObjectId(qr_id)})
    if not doc:
        raise HTTPException(404, "QR code not found")
    scan_count = await db.scan_logs.count_documents({"qr_id": doc["_id"]})
    return _map_qr(doc, scan_count)


@router.put("/{qr_id}", response_model=QRResponse)
async def update_qrcode(event_id: str, qr_id: str, body: QRUpdateRequest, current_user=Depends(get_current_user)):
    db = get_db()
    await _assert_event_access(event_id, current_user, db)
    doc = await db.qr_codes.find_one({"_id": ObjectId(qr_id)})
    if not doc:
        raise HTTPException(404, "QR code not found")

    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    updates["updated_at"] = datetime.utcnow()
    await db.qr_codes.update_one({"_id": ObjectId(qr_id)}, {"$set": updates})
    doc.update(updates)
    scan_count = await db.scan_logs.count_documents({"qr_id": doc["_id"]})
    return _map_qr(doc, scan_count)


@router.delete("/{qr_id}", status_code=204)
async def delete_qrcode(event_id: str, qr_id: str, current_user=Depends(get_current_user)):
    db = get_db()
    await _assert_event_access(event_id, current_user, db)
    doc = await db.qr_codes.find_one({"_id": ObjectId(qr_id)})
    if not doc:
        raise HTTPException(404, "QR code not found")
    await db.qr_codes.delete_one({"_id": ObjectId(qr_id)})
    await db.scan_logs.delete_many({"qr_id": doc["_id"]})


@router.get("/{qr_id}/image")
async def get_qr_image(event_id: str, qr_id: str, current_user=Depends(get_current_user)):
    """Return raw PNG image of the QR code."""
    db = get_db()
    await _assert_event_access(event_id, current_user, db)
    doc = await db.qr_codes.find_one({"_id": ObjectId(qr_id)})
    if not doc:
        raise HTTPException(404, "QR code not found")
    proxy = _proxy_url(doc["short_id"])
    png_bytes = generate_qr_bytes(proxy)
    return Response(content=png_bytes, media_type="image/png")
