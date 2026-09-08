from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..auth_utils import get_current_user_id

router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
)


@router.post("/", response_model=schemas.BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_data: schemas.BookingCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = db.query(models.Service).filter(
        models.Service.id == booking_data.service_id
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    if booking_data.car_id:
        car = db.query(models.Car).filter(
            models.Car.id == booking_data.car_id,
            models.Car.user_id == user_id,
        ).first()
        
        if not car:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Car not found"
            )
    
    new_booking = models.Booking(
        user_id=user_id,
        service_id=booking_data.service_id,
        car_id=booking_data.car_id,
        date=booking_data.date,
        time=booking_data.time,
        address=booking_data.address,
        status="active",
        notes=booking_data.notes,
    )
    
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    
    return new_booking


@router.get("/", response_model=List[schemas.BookingResponse])
def get_bookings(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == user_id
    ).order_by(models.Booking.created_at.desc()).all()
    
    return bookings


@router.get("/{booking_id}", response_model=schemas.BookingResponse)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == user_id,
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    return booking


@router.put("/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == user_id,
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    if booking.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled"
        )
    
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    
    return {"success": True, "message": "Booking cancelled successfully"}