from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone

from ..database import get_db
from .. import models
from ..auth_utils import (
    hash_password,
    verify_password,
    create_admin_token,
    get_current_admin,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Schemas ─────────────────────────────────────────────────
class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class ServiceCreate(BaseModel):
    category: str
    name: str
    description: Optional[str] = None
    price: int


class ServiceUpdate(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None


class ServiceOut(BaseModel):
    id: int
    category: str
    name: str
    description: Optional[str] = ""
    price: int

    class Config:
        from_attributes = True


class MechanicCreate(BaseModel):
    name: str
    phone: str
    password: str
    access_code: str
    is_active: bool = True
    is_available: bool = True
    rating: float = 5.0


class MechanicUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    access_code: Optional[str] = None
    is_active: Optional[bool] = None
    is_available: Optional[bool] = None
    rating: Optional[float] = None


class MechanicOut(BaseModel):
    id: int
    name: str
    phone: str
    access_code: str
    is_active: bool
    is_available: bool
    rating: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BookingOut(BaseModel):
    id: int
    user_id: int
    customer_name: Optional[str] = ""
    customer_phone: Optional[str] = ""
    customer_address: Optional[str] = ""
    service_id: int
    service_name: Optional[str] = ""
    service_price: Optional[int] = 0
    car_id: Optional[int] = None
    assigned_mechanic_id: Optional[int] = None
    mechanic_name: Optional[str] = ""
    date: str
    time: str
    address: str
    status: str
    notes: Optional[str] = ""
    created_at: Optional[datetime] = None


class AssignMechanicRequest(BaseModel):
    mechanic_id: int


class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    email: str
    address: Optional[str] = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    total_bookings: int
    active_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    total_mechanics: int
    active_mechanics: int
    total_services: int
    total_customers: int
    revenue_today: int
    revenue_total: int


# ─── Auth ─────────────────────────────────────────────────────
@router.post("/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest, db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.username == payload.username).first()
    if not admin or not verify_password(payload.password, admin.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_admin_token(admin.id, admin.username)
    return AdminLoginResponse(access_token=token, username=admin.username)


@router.get("/me")
def admin_me(current_admin: models.Admin = Depends(get_current_admin)):
    return {"id": current_admin.id, "username": current_admin.username}


# ─── Stats ────────────────────────────────────────────────────
@router.get("/stats", response_model=StatsOut)
def admin_stats(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    total_bookings = db.query(func.count(models.Booking.id)).scalar() or 0
    active_bookings = db.query(func.count(models.Booking.id)).filter(models.Booking.status == "active").scalar() or 0
    completed_bookings = db.query(func.count(models.Booking.id)).filter(models.Booking.status == "completed").scalar() or 0
    cancelled_bookings = db.query(func.count(models.Booking.id)).filter(models.Booking.status == "cancelled").scalar() or 0
    total_mechanics = db.query(func.count(models.Mechanic.id)).scalar() or 0
    active_mechanics = db.query(func.count(models.Mechanic.id)).filter(models.Mechanic.is_active == True).scalar() or 0
    total_services = db.query(func.count(models.Service.id)).scalar() or 0
    total_customers = db.query(func.count(models.User.id)).scalar() or 0

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    revenue_today = db.query(func.coalesce(func.sum(models.Service.price), 0)).join(models.Booking, models.Booking.service_id == models.Service.id).filter(models.Booking.status == "completed").filter(models.Booking.date == today_str).scalar() or 0
    revenue_total = db.query(func.coalesce(func.sum(models.Service.price), 0)).join(models.Booking, models.Booking.service_id == models.Service.id).filter(models.Booking.status == "completed").scalar() or 0

    return StatsOut(
        total_bookings=total_bookings,
        active_bookings=active_bookings,
        completed_bookings=completed_bookings,
        cancelled_bookings=cancelled_bookings,
        total_mechanics=total_mechanics,
        active_mechanics=active_mechanics,
        total_services=total_services,
        total_customers=total_customers,
        revenue_today=int(revenue_today),
        revenue_total=int(revenue_total),
    )


# ─── Bookings ─────────────────────────────────────────────────
@router.get("/bookings", response_model=List[BookingOut])
def list_bookings(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    bookings = db.query(models.Booking).order_by(models.Booking.created_at.desc()).all()
    out = []
    for b in bookings:
        customer = b.customer
        service = b.service
        mechanic = b.mechanic
        out.append(BookingOut(
            id=b.id,
            user_id=b.user_id,
            customer_name=customer.name if customer and customer.name else "",
            customer_phone=customer.phone if customer and customer.phone else "",
            customer_address=customer.address if customer and customer.address else "",
            service_id=b.service_id,
            service_name=service.name if service and service.name else "",
            service_price=service.price if service and service.price else 0,
            car_id=b.car_id,
            assigned_mechanic_id=b.assigned_mechanic_id,
            mechanic_name=mechanic.name if mechanic and mechanic.name else "",
            date=b.date or "",
            time=b.time or "",
            address=b.address or "",
            status=b.status or "",
            notes=b.notes or "",
            created_at=b.created_at,
        ))
    return out


@router.put("/bookings/{booking_id}/assign", response_model=BookingOut)
def assign_mechanic(
    booking_id: int,
    payload: AssignMechanicRequest,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    mechanic = db.query(models.Mechanic).filter(models.Mechanic.id == payload.mechanic_id).first()
    if not mechanic:
        raise HTTPException(status_code=404, detail="Mechanic not found")
    booking.assigned_mechanic_id = mechanic.id
    db.commit()
    db.refresh(booking)
    customer = booking.customer
    service = booking.service
    return BookingOut(
        id=booking.id,
        user_id=booking.user_id,
        customer_name=customer.name if customer and customer.name else "",
        customer_phone=customer.phone if customer and customer.phone else "",
        customer_address=customer.address if customer and customer.address else "",
        service_id=booking.service_id,
        service_name=service.name if service and service.name else "",
        service_price=service.price if service and service.price else 0,
        car_id=booking.car_id,
        assigned_mechanic_id=booking.assigned_mechanic_id,
        mechanic_name=mechanic.name or "",
        date=booking.date or "",
        time=booking.time or "",
        address=booking.address or "",
        status=booking.status or "",
        notes=booking.notes or "",
        created_at=booking.created_at,
    )


@router.put("/bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    customer = booking.customer
    service = booking.service
    mechanic = booking.mechanic
    return BookingOut(
        id=booking.id,
        user_id=booking.user_id,
        customer_name=customer.name if customer and customer.name else "",
        customer_phone=customer.phone if customer and customer.phone else "",
        customer_address=customer.address if customer and customer.address else "",
        service_id=booking.service_id,
        service_name=service.name if service and service.name else "",
        service_price=service.price if service and service.price else 0,
        car_id=booking.car_id,
        assigned_mechanic_id=booking.assigned_mechanic_id,
        mechanic_name=mechanic.name if mechanic and mechanic.name else "",
        date=booking.date or "",
        time=booking.time or "",
        address=booking.address or "",
        status=booking.status or "",
        notes=booking.notes or "",
        created_at=booking.created_at,
    )


# ─── Mechanics ────────────────────────────────────────────────
@router.get("/mechanics", response_model=List[MechanicOut])
def list_mechanics(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    return db.query(models.Mechanic).order_by(models.Mechanic.id.desc()).all()


@router.post("/mechanics", response_model=MechanicOut)
def create_mechanic(
    payload: MechanicCreate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    existing = db.query(models.Mechanic).filter(models.Mechanic.phone == payload.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone already registered")
    mechanic = models.Mechanic(
        name=payload.name,
        phone=payload.phone,
        password=hash_password(payload.password),
        access_code=payload.access_code,
        is_active=payload.is_active,
        is_available=payload.is_available,
        rating=payload.rating,
    )
    db.add(mechanic)
    db.commit()
    db.refresh(mechanic)
    return mechanic


@router.put("/mechanics/{mechanic_id}", response_model=MechanicOut)
def update_mechanic(
    mechanic_id: int,
    payload: MechanicUpdate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    mechanic = db.query(models.Mechanic).filter(models.Mechanic.id == mechanic_id).first()
    if not mechanic:
        raise HTTPException(status_code=404, detail="Mechanic not found")
    if payload.name is not None:
        mechanic.name = payload.name
    if payload.phone is not None:
        if payload.phone != mechanic.phone:
            clash = db.query(models.Mechanic).filter(models.Mechanic.phone == payload.phone).first()
            if clash:
                raise HTTPException(status_code=400, detail="Phone already registered")
        mechanic.phone = payload.phone
    if payload.password is not None and payload.password != "":
        mechanic.password = hash_password(payload.password)
    if payload.access_code is not None:
        mechanic.access_code = payload.access_code
    if payload.is_active is not None:
        mechanic.is_active = payload.is_active
    if payload.is_available is not None:
        mechanic.is_available = payload.is_available
    if payload.rating is not None:
        mechanic.rating = payload.rating
    db.commit()
    db.refresh(mechanic)
    return mechanic


@router.delete("/mechanics/{mechanic_id}")
def delete_mechanic(
    mechanic_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    mechanic = db.query(models.Mechanic).filter(models.Mechanic.id == mechanic_id).first()
    if not mechanic:
        raise HTTPException(status_code=404, detail="Mechanic not found")
    db.query(models.Booking).filter(models.Booking.assigned_mechanic_id == mechanic_id).update({models.Booking.assigned_mechanic_id: None})
    db.delete(mechanic)
    db.commit()
    return {"ok": True, "deleted_id": mechanic_id}


# ─── Services ─────────────────────────────────────────────────
@router.get("/services", response_model=List[ServiceOut])
def list_services(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    return db.query(models.Service).order_by(models.Service.category, models.Service.id).all()


@router.post("/services", response_model=ServiceOut)
def create_service(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    service = models.Service(
        category=payload.category,
        name=payload.name,
        description=payload.description or "",
        price=payload.price,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.put("/services/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: int,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if payload.category is not None:
        service.category = payload.category
    if payload.name is not None:
        service.name = payload.name
    if payload.description is not None:
        service.description = payload.description
    if payload.price is not None:
        service.price = payload.price
    db.commit()
    db.refresh(service)
    return service


@router.delete("/services/{service_id}")
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    ref_count = db.query(func.count(models.Booking.id)).filter(models.Booking.service_id == service_id).scalar() or 0
    if ref_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete: {ref_count} booking(s) reference this service")
    db.delete(service)
    db.commit()
    return {"ok": True, "deleted_id": service_id}


# ─── Customers ────────────────────────────────────────────────
@router.get("/users", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_admin: models.Admin = Depends(get_current_admin),
):
    return db.query(models.User).order_by(models.User.id.desc()).all()


# ─── Seed default admin ───────────────────────────────────────
def seed_default_admin(db: Session) -> None:
    existing = db.query(models.Admin).first()
    if existing:
        return
    admin = models.Admin(
        username="fixnow_admin",
        password=hash_password("FXN@admin2026"),
    )
    db.add(admin)
    db.commit()
    print("✅ Seeded default admin: fixnow_admin")