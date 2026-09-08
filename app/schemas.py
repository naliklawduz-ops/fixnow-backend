from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ============ USER SCHEMAS ============
class UserRegister(BaseModel):
    name: str
    phone: str
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    phone: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    success: bool
    message: str
    user_id: int


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str = Field(min_length=6)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


# ============ CAR SCHEMAS ============
class CarCreate(BaseModel):
    brand: str
    model: str
    year: int
    color: str
    plate: str


class CarResponse(BaseModel):
    id: int
    user_id: int
    brand: str
    model: str
    year: int
    color: str
    plate: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============ SERVICE SCHEMAS ============
class ServiceResponse(BaseModel):
    id: int
    category: str
    name: str
    description: Optional[str] = None
    price: int

    class Config:
        from_attributes = True


# ============ BOOKING SCHEMAS ============
class BookingCreate(BaseModel):
    service_id: int
    car_id: Optional[int] = None
    date: str
    time: str
    address: str
    notes: Optional[str] = None


class BookingResponse(BaseModel):
    id: int
    user_id: int
    service_id: int
    car_id: Optional[int] = None
    assigned_mechanic_id: Optional[int] = None
    date: str
    time: str
    address: str
    status: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ MECHANIC SCHEMAS ============
class MechanicLogin(BaseModel):
    phone: str
    password: str
    access_code: str


class MechanicResponse(BaseModel):
    id: int
    name: str
    phone: str
    rating: float
    is_available: bool
    access_token: str


class MechanicBookingResponse(BaseModel):
    id: int
    customer_name: str
    customer_phone: str
    customer_address: str
    service_name: str
    service_category: str
    service_price: int
    car_brand: str
    car_model: str
    car_year: Optional[int] = None
    car_color: str
    car_plate: str
    date: str
    time: str
    address: str
    notes: str
    status: str
    created_at: datetime


# ============ CHAT SCHEMAS ============
class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    booking_id: int
    sender_type: str
    sender_name: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True