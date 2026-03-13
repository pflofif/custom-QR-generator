from __future__ import annotations
from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Response, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import shortuuid
import io
from app.database import get_db
from app.auth import get_current_user
from app.schemas import QRCreateRequest, QRUpdateRequest, QRResponse, QRStyleRequest, QRCustomStyle
from app.qr_generator import generate_qr_base64, generate_qr_bytes, generate_amazing_qr_bytes
from app import storage
from app.config import settings

router = APIRouter(prefix="/api/events/{event_id}/qrcodes", tags=["qrcodes"])

_ALLOWED_BG_EXTS = {"jpg", "jpeg", "png", "gif"}
_MAX_BG_SIZE = 2 * 1024 * 1024  # 2 MB


def _proxy_url(short_id: str) -> str:
    return f"{settings.base_url}/r/{short_id}"


def _map_qr(doc: dict, scan_count: int = 0) -> QRResponse:
    custom_style = None
    if doc.get("custom_style"):
        cs = doc["custom_style"]
        custom_style = QRCustomStyle(
            colorized=cs.get("colorized", False),
            contrast=cs.get("contrast", 1.0),
            brightness=cs.get("brightness", 1.0),
            version=cs.get("version", 1),
            level=cs.get("level", "H"),
            has_background=cs.get("has_background", False),
            background_key=cs.get("background_key"),
        )
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
        custom_style=custom_style,
    )


async def _assert_event_access(event_id: str, current_user: dict, db):
    doc = await db.events.find_one({"_id": ObjectId(event_id)})
    if not doc:
        raise HTTPException(404, "Event not found")
    if current_user["role"] != "admin" and str(doc["owner_id"]) != current_user["id"]:
        raise HTTPException(403, "Access denied")
    return doc


async def _build_amazing_qr(doc: dict) -> tuple[bytes, str]:
    """Generate QR bytes using amzqr based on stored custom_style + background."""
    cs = doc.get("custom_style", {})
    proxy = _proxy_url(doc["short_id"])
    bg_bytes: bytes | None = None
    bg_ext = ".png"
    if cs.get("has_background") and cs.get("background_key"):
        try:
            bg_bytes = await storage.download_object(cs["background_key"])
            bg_ext = "." + cs["background_key"].rsplit(".", 1)[-1]
        except Exception:
            pass  # fall back to no background
    return await generate_amazing_qr_bytes(
        proxy,
        background_bytes=bg_bytes,
        background_ext=bg_ext,
        colorized=cs.get("colorized", False),
        contrast=cs.get("contrast", 1.0),
        brightness=cs.get("brightness", 1.0),
        version=cs.get("version", 1),
        level=cs.get("level", "H"),
    )


async def _store_rendered_qr(db, doc: dict) -> dict:
    """Render the QR image and cache it in MinIO. Returns the updated custom_style dict."""
    qr_id = str(doc["_id"])
    img_bytes, mime = await _build_amazing_qr(doc)
    ext = "gif" if mime == "image/gif" else "png"
    rendered_key = f"qr-images/{qr_id}.{ext}"
    await storage.upload_object(rendered_key, img_bytes, mime)
    cs = {**doc.get("custom_style", {}), "rendered_image_key": rendered_key}
    await db.qr_codes.update_one(
        {"_id": doc["_id"]},
        {"$set": {"custom_style": cs}},
    )
    return cs


# â”€â”€â”€ Standard CRUD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("", response_model=QRResponse, status_code=201)
async def create_qrcode(event_id: str, body: QRCreateRequest, current_user=Depends(get_current_user)):
    db = get_db()
    event = await _assert_event_access(event_id, current_user, db)
    short_id = shortuuid.ShortUUID().random(length=8)
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
    # Clean up stored background if any
    cs = doc.get("custom_style", {})
    if cs.get("background_key"):
        await storage.delete_object(cs["background_key"])
    await db.qr_codes.delete_one({"_id": ObjectId(qr_id)})
    await db.scan_logs.delete_many({"qr_id": doc["_id"]})


# â”€â”€â”€ Image endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/{qr_id}/image")
async def get_qr_image(event_id: str, qr_id: str, current_user=Depends(get_current_user)):
    """Return the QR image. Serves the cached MinIO copy if available, otherwise generates."""
    db = get_db()
    await _assert_event_access(event_id, current_user, db)
    doc = await db.qr_codes.find_one({"_id": ObjectId(qr_id)})
    if not doc:
        raise HTTPException(404, "QR code not found")

    cs = doc.get("custom_style")
    if cs:
        # Serve from MinIO cache; generate + cache on first hit or after invalidation
        rendered_key = cs.get("rendered_image_key")
        if rendered_key:
            try:
                img_bytes = await storage.download_object(rendered_key)
                ext = rendered_key.rsplit(".", 1)[-1]
                mime = "image/gif" if ext == "gif" else "image/png"
                return Response(content=img_bytes, media_type=mime)
            except Exception:
                pass  # cache miss — fall through to regenerate
        # Cache miss: generate and store
        cs = await _store_rendered_qr(db, doc)
        rendered_key = cs["rendered_image_key"]
        img_bytes = await storage.download_object(rendered_key)
        ext = rendered_key.rsplit(".", 1)[-1]
        return Response(content=img_bytes, media_type="image/gif" if ext == "gif" else "image/png")

    png_bytes = generate_qr_bytes(_proxy_url(doc["short_id"]))
    return Response(content=png_bytes, media_type="image/png")


@router.post("/{qr_id}/preview")
async def preview_qr(
    event_id: str,
    qr_id: str,
    current_user=Depends(get_current_user),
    background: Optional[UploadFile] = File(None),
    colorized: bool = Form(False),
    contrast: float = Form(1.0),
    brightness: float = Form(1.0),
    version: int = Form(1),
    level: str = Form("H"),
    ignore_stored_bg: bool = Form(False),
):
    """Generate a QR preview on-the-fly without saving. Used by the frontend live preview."""
    db = get_db()
    await _assert_event_access(event_id, current_user, db)
    doc = await db.qr_codes.find_one({"_id": ObjectId(qr_id)})
    if not doc:
        raise HTTPException(404, "QR code not found")

    proxy = _proxy_url(doc["short_id"])
    bg_bytes: bytes | None = None
    bg_ext = ".png"

    if background and background.filename:
        ext = background.filename.rsplit(".", 1)[-1].lower() if "." in background.filename else ""
        if ext not in _ALLOWED_BG_EXTS:
            raise HTTPException(400, "Unsupported file type. Use JPG, PNG or GIF.")
        content = await background.read()
        if len(content) > _MAX_BG_SIZE:
            raise HTTPException(400, "Background image must be under 2 MB")
        bg_bytes = content
        bg_ext = f".{ext}"
    elif not ignore_stored_bg:
        cs = doc.get("custom_style", {})
        if cs.get("has_background") and cs.get("background_key"):
            try:
                bg_bytes = await storage.download_object(cs["background_key"])
                bg_ext = "." + cs["background_key"].rsplit(".", 1)[-1]
            except Exception:
                pass

    level = level if level in ("L", "M", "Q", "H") else "H"
    version = max(1, min(40, version))

    img_bytes, mime = await generate_amazing_qr_bytes(
        proxy,
        background_bytes=bg_bytes,
        background_ext=bg_ext,
        colorized=colorized,
        contrast=contrast,
        brightness=brightness,
        version=version,
        level=level,
    )
    return Response(content=img_bytes, media_type=mime)


# â”€â”€â”€ Custom style endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/{qr_id}/style", response_model=QRResponse)
async def set_qr_style(
    event_id: str,
    qr_id: str,
    body: QRStyleRequest,
    current_user=Depends(get_current_user),
):
    """Save custom style params (colorized, contrast, brightness, version, level)."""
    db = get_db()
    await _assert_event_access(event_id, current_user, db)
    doc = await db.qr_codes.find_one({"_id": ObjectId(qr_id)})
    if not doc:
        raise HTTPException(404, "QR code not found")

    existing_cs = doc.get("custom_style", {})
    custom_style = {
        "colorized": body.colorized,
        "contrast": body.contrast,
        "brightness": body.brightness,
        "version": body.version,
        "level": body.level,
        # preserve background info
        "has_background": existing_cs.get("has_background", False),
        "background_key": existing_cs.get("background_key"),
        "rendered_image_key": None,  # invalidate cache
    }
    now = datetime.utcnow()
    await db.qr_codes.update_one(
        {"_id": ObjectId(qr_id)},
        {"$set": {"custom_style": custom_style, "updated_at": now}},
    )
    doc["custom_style"] = custom_style
    doc["updated_at"] = now
    # Render and cache immediately so download is instant
    doc["custom_style"] = await _store_rendered_qr(db, doc)
    scan_count = await db.scan_logs.count_documents({"qr_id": doc["_id"]})
    return _map_qr(doc, scan_count)


@router.delete("/{qr_id}/style", status_code=204)
async def reset_qr_style(event_id: str, qr_id: str, current_user=Depends(get_current_user)):
    """Remove all custom styling (including background) and revert to plain QR."""
    db = get_db()
    await _assert_event_access(event_id, current_user, db)
    doc = await db.qr_codes.find_one({"_id": ObjectId(qr_id)})
    if not doc:
        raise HTTPException(404, "QR code not found")
    cs = doc.get("custom_style", {})
    # Delete all stored objects for this QR
    for key_field in ("background_key", "rendered_image_key"):
        if cs.get(key_field):
            await storage.delete_object(cs[key_field])
    await db.qr_codes.update_one(
        {"_id": ObjectId(qr_id)},
        {"$unset": {"custom_style": ""}, "$set": {"updated_at": datetime.utcnow()}},
    )


@router.post("/{qr_id}/background", response_model=QRResponse)
async def upload_qr_background(
    event_id: str,
    qr_id: str,
    current_user=Depends(get_current_user),
    background: UploadFile = File(...),
):
    """Upload a background image for the custom QR (JPG/PNG/GIF, max 2 MB)."""
    db = get_db()
    await _assert_event_access(event_id, current_user, db)
    doc = await db.qr_codes.find_one({"_id": ObjectId(qr_id)})
    if not doc:
        raise HTTPException(404, "QR code not found")

    fname = background.filename or ""
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if ext not in _ALLOWED_BG_EXTS:
        raise HTTPException(400, "Unsupported file type. Use JPG, PNG or GIF.")

    content = await background.read()
    if len(content) > _MAX_BG_SIZE:
        raise HTTPException(400, "Background image must be under 2 MB")

    object_key = f"backgrounds/{qr_id}.{ext}"
    mime_type = background.content_type or f"image/{ext}"
    await storage.upload_object(object_key, content, mime_type)

    existing_cs = doc.get("custom_style", {})
    # Remove old background from MinIO if key changed
    old_key = existing_cs.get("background_key")
    if old_key and old_key != object_key:
        await storage.delete_object(old_key)

    custom_style = {
        **existing_cs,
        "has_background": True,
        "background_key": object_key,
        "rendered_image_key": None,  # invalidate cache
    }
    now = datetime.utcnow()
    await db.qr_codes.update_one(
        {"_id": ObjectId(qr_id)},
        {"$set": {"custom_style": custom_style, "updated_at": now}},
    )
    doc["custom_style"] = custom_style
    doc["updated_at"] = now
    # Render and cache immediately
    doc["custom_style"] = await _store_rendered_qr(db, doc)
    scan_count = await db.scan_logs.count_documents({"qr_id": doc["_id"]})
    return _map_qr(doc, scan_count)


@router.delete("/{qr_id}/background", status_code=204)
async def delete_qr_background(event_id: str, qr_id: str, current_user=Depends(get_current_user)):
    """Remove the background image, keeping other style settings intact."""
    db = get_db()
    await _assert_event_access(event_id, current_user, db)
    doc = await db.qr_codes.find_one({"_id": ObjectId(qr_id)})
    if not doc:
        raise HTTPException(404, "QR code not found")
    cs = doc.get("custom_style", {})
    for key_field in ("background_key", "rendered_image_key"):
        if cs.get(key_field):
            await storage.delete_object(cs[key_field])
    custom_style = {**cs, "has_background": False, "background_key": None, "rendered_image_key": None}
    now = datetime.utcnow()
    await db.qr_codes.update_one(
        {"_id": ObjectId(qr_id)},
        {"$set": {"custom_style": custom_style, "updated_at": now}},
    )
    doc["custom_style"] = custom_style
    doc["updated_at"] = now
    # Regenerate cache without background
    await _store_rendered_qr(db, doc)

