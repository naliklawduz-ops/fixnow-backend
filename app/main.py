from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth, cars, services, bookings, chat, mechanic

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FIX.NOW API", description="On-demand service booking app", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(cars.router)
app.include_router(services.router)
app.include_router(bookings.router)
app.include_router(chat.router)
app.include_router(mechanic.router)  # NEW


@app.get("/")
def root():
    return {"message": "FIX.NOW API is running", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}