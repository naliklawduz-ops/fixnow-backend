import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from . import models

# ─── Config ──────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "fixnow_secret_key_2024")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Customer / mechanic tokens: 100 years
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 365 * 100

# Admin tokens: 8 hours
ADMIN_TOKEN_EXPIRE_MINUTES = 60 * 8

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


# ─── Password helpers ────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─── Token creation ──────────────────────────────────────────
def create_token(user_id: int, phone: str) -> str:
    payload = {
        "sub": str(user_id),
        "phone": phone,
        "type": "customer",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_mechanic_token(mechanic_id: int, phone: str) -> str:
    payload = {
        "sub": str(mechanic_id),
        "phone": phone,
        "type": "mechanic",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_admin_token(admin_id: int, username: str) -> str:
    payload = {
        "sub": str(admin_id),
        "username": username,
        "type": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ADMIN_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ─── Token decoding ──────────────────────────────────────────
def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def _extract_bearer(credentials: Optional[HTTPAuthorizationCredentials]) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )
    return credentials.credentials


# ─── Customer dependencies ───────────────────────────────────
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> models.User:
    token = _extract_bearer(credentials)
    payload = _decode_token(token)
    if payload.get("type") != "customer":
        raise HTTPException(status_code=401, detail="Not a customer token")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> int:
    token = _extract_bearer(credentials)
    payload = _decode_token(token)
    if payload.get("type") != "customer":
        raise HTTPException(status_code=401, detail="Not a customer token")
    return int(payload["sub"])


# ─── Mechanic dependency ─────────────────────────────────────
def get_current_mechanic(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> models.Mechanic:
    token = _extract_bearer(credentials)
    payload = _decode_token(token)
    if payload.get("type") != "mechanic":
        raise HTTPException(status_code=401, detail="Not a mechanic token")
    mechanic_id = payload.get("sub")
    if mechanic_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    mechanic = db.query(models.Mechanic).filter(models.Mechanic.id == int(mechanic_id)).first()
    if mechanic is None:
        raise HTTPException(status_code=401, detail="Mechanic not found")
    return mechanic


# ─── Admin dependency ────────────────────────────────────────
def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> models.Admin:
    token = _extract_bearer(credentials)
    payload = _decode_token(token)
    if payload.get("type") != "admin":
        raise HTTPException(status_code=401, detail="Not an admin token")
    admin_id = payload.get("sub")
    if admin_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    admin = db.query(models.Admin).filter(models.Admin.id == int(admin_id)).first()
    if admin is None:
        raise HTTPException(status_code=401, detail="Admin not found")
    return admin