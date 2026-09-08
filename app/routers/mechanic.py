from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import Mechanic, Booking, User, Service, Car
from ..schemas import MechanicLogin, MechanicResponse, MechanicBookingResponse, MessageResponse
from ..auth_utils import (
    hash_password,
    verify_password,
    create_mechanic_token,
    get_current_mechanic,
)

router = APIRouter(prefix="/mechanic", tags=["mechanic"])


@router.post("/login", response_model=MechanicResponse)
def mechanic_login(login_data: MechanicLogin, db: Session = Depends(get_db)):
    # Find mechanic by phone
    mechanic = db.query(Mechanic).filter(Mechanic.phone == login_data.phone).first()

    if not mechanic:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone, password, or access code",
        )

    # Check if account is active
    if not mechanic.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact administrator.",
        )

    # Verify password
    if not verify_password(login_data.password, mechanic.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone, password, or access code",
        )

    # Verify access code
    if login_data.access_code != mechanic.access_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone, password, or access code",
        )

    # Generate mechanic JWT token
    token = create_mechanic_token(mechanic.id, mechanic.phone)

    return MechanicResponse(
        id=mechanic.id,
        name=mechanic.name,
        phone=mechanic.phone,
        rating=mechanic.rating,
        is_available=mechanic.is_available,
        access_token=token,
    )


@router.get("/bookings", response_model=List[MechanicBookingResponse])
def get_mechanic_bookings(
    current_mechanic: Mechanic = Depends(get_current_mechanic),
    db: Session = Depends(get_db),
):
    # Get all bookings assigned to this mechanic
    bookings = (
        db.query(Booking)
        .filter(Booking.assigned_mechanic_id == current_mechanic.id)
        .filter(Booking.status == "active")
        .order_by(Booking.created_at.desc())
        .all()
    )

    result = []
    for booking in bookings:
        customer = db.query(User).filter(User.id == booking.user_id).first()
        service = db.query(Service).filter(Service.id == booking.service_id).first()
        car = db.query(Car).filter(Car.id == booking.car_id).first() if booking.car_id else None

        result.append(
            MechanicBookingResponse(
                id=booking.id,
                customer_name=customer.name if customer else "Unknown",
                customer_phone=customer.phone if customer else "Unknown",
                customer_address=customer.address if customer else "",
                service_name=service.name if service else "Unknown",
                service_category=service.category if service else "Unknown",
                service_price=service.price if service else 0,
                car_brand=car.brand if car else "",
                car_model=car.model if car else "",
                car_year=car.year if car else None,
                car_color=car.color if car else "",
                car_plate=car.plate if car else "",
                date=booking.date,
                time=booking.time,
                address=booking.address,
                notes=booking.notes if booking.notes else "",
                status=booking.status,
                created_at=booking.created_at,
            )
        )

    return result


@router.put("/bookings/{booking_id}/complete")
def complete_booking(
    booking_id: int,
    current_mechanic: Mechanic = Depends(get_current_mechanic),
    db: Session = Depends(get_db),
):
    # Find booking
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # Check if booking is assigned to this mechanic
    if booking.assigned_mechanic_id != current_mechanic.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Booking is not assigned to you",
        )

    # Check if booking is active
    if booking.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already completed or cancelled",
        )

    # Mark as completed
    booking.status = "completed"
    db.commit()

    return {"message": "Booking marked as completed successfully"}


@router.get("/profile", response_model=MechanicResponse)
def get_mechanic_profile(
    current_mechanic: Mechanic = Depends(get_current_mechanic),
):
    return MechanicResponse(
        id=current_mechanic.id,
        name=current_mechanic.name,
        phone=current_mechanic.phone,
        rating=current_mechanic.rating,
        is_available=current_mechanic.is_available,
        access_token="",  # Don't return token for profile fetch
    )