from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.storage import ensure_bucket

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.qr_codes.create_index("short_id", unique=True)
    await db.qr_codes.create_index("event_id")
    await db.scan_logs.create_index("short_id")
    await db.scan_logs.create_index("event_id")
    await db.scan_logs.create_index("scanned_at")
    await db.events.create_index("owner_id")
    print("Connected to MongoDB and indexes created.")
    await ensure_bucket()
    print(f"MinIO bucket '{settings.minio_bucket}' ready.")
    await _seed_admin()


async def _seed_admin():
    """Create default admin account if no admin exists yet."""
    from datetime import datetime
    from passlib.context import CryptContext

    existing = await db.users.find_one({"role": "admin"})
    if existing:
        return

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("admin123")
    await db.users.insert_one({
        "username": "admin",
        "email": "admin@qrplatform.io",
        "hashed_password": pwd,
        "role": "admin",
        "telegram_chat_id": None,
        "is_active": True,
        "created_at": datetime.utcnow(),
    })
    print("✅ Default admin created → admin@qrplatform.io / admin123  (change this password!)")


async def close_db():
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")


def get_db():
    return db
