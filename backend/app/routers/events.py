from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, status
from app.database import get_db
from app.auth import get_current_user, require_admin
from app.schemas import EventCreateRequest, EventUpdateRequest, EventResponse

router = APIRouter(prefix="/api/events", tags=["events"])


def _map_event(doc: dict, qr_count: int = 0, total_scans: int = 0) -> EventResponse:
    return EventResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        description=doc.get("description"),
        owner_id=str(doc["owner_id"]),
        is_active=doc.get("is_active", True),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        qr_count=qr_count,
        total_scans=total_scans,
    )


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(body: EventCreateRequest, current_user=Depends(get_current_user)):
    db = get_db()
    now = datetime.utcnow()
    doc = {
        "name": body.name,
        "description": body.description,
        "owner_id": ObjectId(current_user["id"]),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.events.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _map_event(doc)


@router.get("", response_model=list[EventResponse])
async def list_events(current_user=Depends(get_current_user)):
    db = get_db()
    query = {} if current_user["role"] == "admin" else {"owner_id": ObjectId(current_user["id"])}
    events = []
    async for doc in db.events.find(query).sort("created_at", -1):
        event_id = doc["_id"]
        qr_count = await db.qr_codes.count_documents({"event_id": event_id})
        total_scans = await db.scan_logs.count_documents({"event_id": event_id})
        events.append(_map_event(doc, qr_count, total_scans))
    return events


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, current_user=Depends(get_current_user)):
    db = get_db()
    doc = await db.events.find_one({"_id": ObjectId(event_id)})
    if not doc:
        raise HTTPException(404, "Event not found")
    if current_user["role"] != "admin" and str(doc["owner_id"]) != current_user["id"]:
        raise HTTPException(403, "Access denied")
    qr_count = await db.qr_codes.count_documents({"event_id": doc["_id"]})
    total_scans = await db.scan_logs.count_documents({"event_id": doc["_id"]})
    return _map_event(doc, qr_count, total_scans)


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(event_id: str, body: EventUpdateRequest, current_user=Depends(get_current_user)):
    db = get_db()
    doc = await db.events.find_one({"_id": ObjectId(event_id)})
    if not doc:
        raise HTTPException(404, "Event not found")
    if current_user["role"] != "admin" and str(doc["owner_id"]) != current_user["id"]:
        raise HTTPException(403, "Access denied")

    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    updates["updated_at"] = datetime.utcnow()
    await db.events.update_one({"_id": ObjectId(event_id)}, {"$set": updates})
    doc.update(updates)
    qr_count = await db.qr_codes.count_documents({"event_id": doc["_id"]})
    total_scans = await db.scan_logs.count_documents({"event_id": doc["_id"]})
    return _map_event(doc, qr_count, total_scans)


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: str, current_user=Depends(get_current_user)):
    db = get_db()
    doc = await db.events.find_one({"_id": ObjectId(event_id)})
    if not doc:
        raise HTTPException(404, "Event not found")
    if current_user["role"] != "admin" and str(doc["owner_id"]) != current_user["id"]:
        raise HTTPException(403, "Access denied")
    await db.events.delete_one({"_id": ObjectId(event_id)})
    await db.qr_codes.delete_many({"event_id": doc["_id"]})
    await db.scan_logs.delete_many({"event_id": doc["_id"]})
