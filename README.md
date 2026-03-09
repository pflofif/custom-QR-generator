# QR Code Management & Analytics Platform

A full-stack SaaS-style platform for creating and managing **dynamic QR codes** with real-time analytics. Change destination URLs without reprinting QR codes.

---

## Architecture

```
User → QR Code (printed) → /r/{short_id} (proxy) → target_url (updatable)
                                    ↓
                              Scan logged (analytics)
```

### Tech Stack

| Layer     | Technology                                   |
|-----------|----------------------------------------------|
| Backend   | Python · FastAPI · Motor (async MongoDB)     |
| Database  | MongoDB                                      |
| Frontend  | Next.js 14 · Tailwind CSS · Recharts · Lucide |
| Auth      | JWT (python-jose) · bcrypt                   |
| QR Gen    | python-qrcode · Pillow                       |

---

## Features

- **JWT Auth** with Admin / User roles
- **Event-based hierarchy**: User → Events → QR Codes
- **Dynamic proxy redirect** at `/r/{short_id}` with background scan logging
- **QR code generation** (high-quality PNG, downloadable)
- **Analytics dashboard**: time-series, per-QR comparison, device + browser breakdown
- **Telegram-ready** schema (`telegram_chat_id`, `telegram_user_id` fields)

---

## Quick Start (Docker)

```bash
git clone <repo>
cd qr-generator

# Start everything
docker compose up --build
```

| Service   | URL                    |
|-----------|------------------------|
| Frontend  | http://localhost:3000  |
| Backend   | http://localhost:8000  |
| API Docs  | http://localhost:8000/docs |

---

## Manual Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt

# Copy and configure environment variables
copy .env.example .env

# Run
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install

# Copy environment variables
copy .env.local.example .env.local   # or create manually

npm run dev
```

### MongoDB

Use [MongoDB Community Server](https://www.mongodb.com/try/download/community) locally or [MongoDB Atlas](https://cloud.mongodb.com/).

Update `MONGODB_URL` in `backend/.env` accordingly.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable                      | Description                             |
|-------------------------------|-----------------------------------------|
| `MONGODB_URL`                 | MongoDB connection string               |
| `DATABASE_NAME`               | Database name (default: `qr_platform`)  |
| `SECRET_KEY`                  | JWT secret key (min 32 chars)           |
| `ALGORITHM`                   | JWT algorithm (default: `HS256`)        |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL (default: `10080` = 7 days)  |
| `BASE_URL`                    | Public backend URL (for proxy links)    |
| `FRONTEND_URL`                | Frontend origin (for CORS)              |

### Frontend (`frontend/.env.local`)

| Variable               | Description              |
|------------------------|--------------------------|
| `NEXT_PUBLIC_API_URL`  | Backend API base URL     |

---

## API Reference

### Auth
| Method | Path               | Description          |
|--------|--------------------|----------------------|
| POST   | `/api/auth/register` | Register new user  |
| POST   | `/api/auth/login`    | Login → JWT token  |
| GET    | `/api/auth/me`       | Get current user   |

### Events
| Method | Path                  | Description              |
|--------|-----------------------|--------------------------|
| GET    | `/api/events`         | List all events          |
| POST   | `/api/events`         | Create event             |
| GET    | `/api/events/{id}`    | Get event details        |
| PUT    | `/api/events/{id}`    | Update event             |
| DELETE | `/api/events/{id}`    | Delete event + all QRs   |

### QR Codes
| Method | Path                                          | Description           |
|--------|-----------------------------------------------|-----------------------|
| GET    | `/api/events/{id}/qrcodes`                    | List QR codes         |
| POST   | `/api/events/{id}/qrcodes`                    | Create QR code        |
| GET    | `/api/events/{id}/qrcodes/{qr_id}`            | Get QR code           |
| PUT    | `/api/events/{id}/qrcodes/{qr_id}`            | Update QR / URL       |
| DELETE | `/api/events/{id}/qrcodes/{qr_id}`            | Delete QR code        |
| GET    | `/api/events/{id}/qrcodes/{qr_id}/image`      | Download PNG image    |

### Redirect (Proxy)
| Method | Path             | Description                                  |
|--------|------------------|----------------------------------------------|
| GET    | `/r/{short_id}`  | Log scan + 302 redirect to `target_url`      |

### Analytics
| Method | Path                              | Params      | Description              |
|--------|-----------------------------------|-------------|--------------------------|
| GET    | `/api/analytics/overview`         | —           | Global dashboard stats   |
| GET    | `/api/analytics/events/{id}`      | `?days=30`  | Per-event analytics      |

Full interactive docs: **http://localhost:8000/docs**

---

## MongoDB Schema

### `users`
```json
{ "_id", "username", "email", "hashed_password", "role", "telegram_chat_id", "is_active", "created_at" }
```

### `events`
```json
{ "_id", "name", "description", "owner_id", "is_active", "created_at", "updated_at" }
```

### `qr_codes`
```json
{ "_id", "short_id", "label", "target_url", "event_id", "owner_id", "is_active", "created_at", "updated_at" }
```

### `scan_logs`
```json
{ "_id", "short_id", "qr_id", "event_id", "owner_id", "ip_address", "user_agent",
  "device_type", "os", "browser", "scanned_at", "telegram_user_id" }
```

---

## Use Case: Hackathon 2025

1. Register / Login
2. Create event **"Hackathon 2025"**
3. Add 3 QR codes: _Entrance Poster_, _Table Stickers_, _LinkedIn Post_
4. Download PNG images → print / share
5. If the registration URL changes → click **Edit** on any QR code → update URL → **all physical QRs continue working**
6. Check **Analytics** to see which placement drives the most registrations

---

## Telegram Integration (Future)

The schema includes `telegram_chat_id` on users and `telegram_user_id` on scan logs.
A Telegram Bot can:
- Look up users by `chat_id`
- Create/manage events via bot commands
- Post scan alerts to a Telegram channel

---

## License

MIT
