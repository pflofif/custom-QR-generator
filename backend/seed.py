"""
Seed script — creates the first admin user.
Run: python seed.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from passlib.context import CryptContext

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "qr_platform"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]

    email = "admin@qrplatform.io"
    existing = await db.users.find_one({"email": email})
    if existing:
        print("Admin user already exists.")
        client.close()
        return

    await db.users.insert_one({
        "username": "admin",
        "email": email,
        "hashed_password": pwd_context.hash("admin123"),
        "role": "admin",
        "telegram_chat_id": None,
        "is_active": True,
        "created_at": datetime.utcnow(),
    })
    print(f"Admin user created: {email} / admin123")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
