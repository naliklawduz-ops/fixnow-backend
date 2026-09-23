from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os

from .database import engine, Base, SessionLocal
from .routers import auth, cars, services, bookings, chat, mechanic, admin, maintenance
from .routers.admin import seed_default_admin

# ─── Create tables ───────────────────────────────────────────
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")
except Exception as e:
    print(f"⚠️ Database connection error: {e}")

# ─── Seed default admin ──────────────────────────────────────
try:
    db = SessionLocal()
    try:
        seed_default_admin(db)
    finally:
        db.close()
except Exception as e:
    print(f"⚠️ Admin seed skipped: {e}")

# ─── Rate limiter ─────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="FIX.NOW API",
    description="On-demand service booking app",
    version="1.0.0",
    docs_url=None,      # ← Disable /docs
    redoc_url=None,     # ← Disable /redoc
    openapi_url=None,   # ← Disable /openapi.json
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://fixnow-backend-production-f6af.up.railway.app",
        "http://localhost",
        "http://localhost:8080",
        "http://10.0.2.2",        # Android emulator
        "http://10.0.2.2:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ─── Static files ────────────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ─── Routers ─────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(cars.router)
app.include_router(services.router)
app.include_router(bookings.router)
app.include_router(chat.router)
app.include_router(mechanic.router)
app.include_router(admin.router)
app.include_router(maintenance.router)


@app.get("/")
def root():
    return {"message": "FIX.NOW API is running", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
