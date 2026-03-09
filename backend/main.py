from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import connect_db, close_db
from app.config import settings
from app.routers import auth, events, qrcodes, redirect, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="QR Code Management & Analytics Platform",
    version="1.0.0",
    description="Dynamic QR code generation with proxy redirection and analytics.",
    lifespan=lifespan,
)

# CORS ─────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers ──────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(qrcodes.router)
app.include_router(redirect.router)
app.include_router(analytics.router)


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "message": "QR Platform API is running."}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}
