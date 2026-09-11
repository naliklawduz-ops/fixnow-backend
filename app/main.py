from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth, cars, services, bookings, chat, mechanic

try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")
except Exception as e:
    print(f"⚠️ Database connection error: {e}")

app = FastAPI(title="FIX.NOW API", description="On-demand service booking app", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cars.router)
app.include_router(services.router)
app.include_router(bookings.router)
app.include_router(chat.router)
app.include_router(mechanic.router)

@app.get("/")
def root():
    return {"message": "FIX.NOW API is running", "status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}