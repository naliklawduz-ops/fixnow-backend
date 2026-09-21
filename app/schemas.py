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
    current_km: Optional[int] = None
    estimated_km_per_month: Optional[int] = 1000


class CarResponse(BaseModel):
    id: int
    user_id: int
    brand: str
    model: str
    year: int
    color: str
    plate: str
    current_km: Optional[int] = None
    estimated_km_per_month: Optional[int] = 1000
    created_at: datetime

    class Config:
        from_attributes = True


class CarKmUpdate(BaseModel):
    current_km: int = Field(ge=0)
    estimated_km_per_month: Optional[int] = Field(default=None, ge=0)


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
    service_name: Optional[str] = None
    service_category: Optional[str] = None
    service_price: Optional[int] = None
    car_id: Optional[int] = None
    assigned_mechanic_id: Optional[int] = None
    mechanic_name: Optional[str] = None
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
    service_id: int
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
    car_current_km: Optional[int] = None
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


# ============ MAINTENANCE SCHEMAS ============

# ----- Admin: Parts -----
class MaintenancePartCreate(BaseModel):
    name: str
    default_interval_km: int = Field(gt=0)
    service_id: Optional[int] = None
    is_active: bool = True


class MaintenancePartUpdate(BaseModel):
    name: Optional[str] = None
    default_interval_km: Optional[int] = Field(default=None, gt=0)
    service_id: Optional[int] = None
    is_active: Optional[bool] = None


class MaintenancePartResponse(BaseModel):
    id: int
    name: str
    default_interval_km: int
    service_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    brands: List["MaintenanceBrandResponse"] = []

    class Config:
        from_attributes = True


# ----- Admin: Brands -----
class MaintenanceBrandCreate(BaseModel):
    part_id: int
    brand_name: str
    interval_km: int = Field(gt=0)
    is_active: bool = True


class MaintenanceBrandUpdate(BaseModel):
    brand_name: Optional[str] = None
    interval_km: Optional[int] = Field(default=None, gt=0)
    is_active: Optional[bool] = None


class MaintenanceBrandResponse(BaseModel):
    id: int
    part_id: int
    brand_name: str
    interval_km: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ----- Customer: Car Maintenance Status -----
class MaintenanceItemStatus(BaseModel):
    part_id: int
    part_name: str
    last_changed_km: Optional[int] = None
    last_changed_at: Optional[datetime] = None
    last_changed_brand_id: Optional[int] = None
    last_changed_brand_name: Optional[str] = None
    next_change_km: Optional[int] = None
    km_remaining: Optional[int] = None
    status: str
    source: Optional[str] = None
    service_id: Optional[int] = None
    service_category: Optional[str] = None
    estimated_months_remaining: Optional[float] = None
    available_brands: List[MaintenanceBrandResponse] = []


class CarMaintenanceSummary(BaseModel):
    car_id: int
    car_name: str
    current_km: Optional[int] = None
    estimated_km_per_month: Optional[int] = 1000
    total_parts: int
    red_count: int
    yellow_count: int
    green_count: int
    items: List[MaintenanceItemStatus] = []


# ----- Manual Reset by Customer -----
class CarMaintenanceResetRequest(BaseModel):
    last_changed_km: int = Field(ge=0)
    brand_id: Optional[int] = None


# ----- Mechanic: Complete with Brand -----
class CompleteWithBrandRequest(BaseModel):
    brand_id: Optional[int] = None
    notes: Optional[str] = None
    current_km: Optional[int] = Field(default=None, ge=0)


class CompleteWithBrandResponse(BaseModel):
    success: bool
    message: str
    booking_id: int
    maintenance_updated: bool
    updated_part_name: Optional[str] = None


# Resolve forward reference
MaintenancePartResponse.model_rebuild()