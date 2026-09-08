from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import Dict, Optional
import bcrypt
import jwt
import os
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, Field

from ..database import get_db
from .. import models, schemas
from ..auth_utils import get_current_user_id
from ..email_service import generate_reset_code, send_reset_email

load_dotenv()

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

JWT_SECRET = os.getenv("JWT_SECRET", "your_secret_key_here")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_HOURS = 24

login_attempts: Dict[str, list] = {}
reset_codes: Dict[str, dict] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 30
RESET_CODE_EXPIRY_MINUTES = 10


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_jwt_token(user_id: int, phone: str) -> str:
    payload = {
        "user_id": user_id,
        "phone": phone,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRES_HOURS),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def check_rate_limit(phone: str) -> bool:
    now = datetime.utcnow()
    
    if phone in login_attempts:
        login_attempts[phone] = [
            attempt for attempt in login_attempts[phone]
            if now - attempt < timedelta(minutes=LOCKOUT_MINUTES)
        ]
        
        if len(login_attempts[phone]) >= MAX_LOGIN_ATTEMPTS:
            return True
    
    return False


def record_failed_attempt(phone: str):
    now = datetime.utcnow()
    if phone not in login_attempts:
        login_attempts[phone] = []
    login_attempts[phone].append(now)


def clear_attempts(phone: str):
    if phone in login_attempts:
        del login_attempts[phone]


@router.post("/register", response_model=schemas.RegisterResponse)
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(
        models.User.phone == user_data.phone
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    if user_data.email:
        existing_email = db.query(models.User).filter(
            models.User.email == user_data.email
        ).first()
        
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    hashed_password = hash_password(user_data.password)
    
    new_user = models.User(
        name=user_data.name,
        phone=user_data.phone,
        email=user_data.email,
        password=hashed_password,
        address=None,
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again."
        )
    
    return schemas.RegisterResponse(
        success=True,
        message="Registration successful",
        user_id=new_user.id,
    )


@router.post("/login", response_model=schemas.LoginResponse)
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    phone = user_data.phone.replace(' ', '').replace('-', '')
    
    if check_rate_limit(phone):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please try again in {LOCKOUT_MINUTES} minutes."
        )
    
    user = db.query(models.User).filter(
        models.User.phone == phone
    ).first()
    
    if not user:
        record_failed_attempt(phone)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or password"
        )
    
    if not verify_password(user_data.password, user.password):
        record_failed_attempt(phone)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or password"
        )
    
    clear_attempts(phone)
    
    token = create_jwt_token(user.id, user.phone)
    
    return schemas.LoginResponse(
        success=True,
        message="Login successful",
        token=token,
        user=schemas.UserResponse.from_orm(user),
    )


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.email == request.email
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email"
        )
    
    code = generate_reset_code()
    expires_at = datetime.utcnow() + timedelta(minutes=RESET_CODE_EXPIRY_MINUTES)
    
    reset_codes[request.email] = {
        "code": code,
        "expires_at": expires_at,
    }
    
    email_sent = send_reset_email(request.email, code)
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email. Please try again."
        )
    
    return {"success": True, "message": "Reset code sent to your email"}


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    stored = reset_codes.get(request.email)
    
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No reset code requested for this email"
        )
    
    if datetime.utcnow() > stored["expires_at"]:
        del reset_codes[request.email]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code has expired"
        )
    
    if stored["code"] != request.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset code"
        )
    
    user = db.query(models.User).filter(
        models.User.email == request.email
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.password = hash_password(request.new_password)
    db.commit()
    
    del reset_codes[request.email]
    
    return {"success": True, "message": "Password reset successfully"}


@router.put("/change-password")
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not verify_password(request.current_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    user.password = hash_password(request.new_password)
    db.commit()
    
    return {"success": True, "message": "Password changed successfully"}