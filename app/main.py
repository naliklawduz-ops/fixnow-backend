from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .database import engine, Base, SessionLocal
from .routers import auth, cars, services, bookings, chat, mechanic, admin
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

app = FastAPI(
    title="FIX.NOW API",
    description="On-demand service booking app",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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


@app.get("/")
def root():
    return {"message": "FIX.NOW API is running", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}