from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from ..database import get_db
from .. import models, schemas
from ..auth_utils import get_current_user_id, get_current_mechanic

router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
)


# ============================================================
# CUSTOMER ENDPOINTS (unchanged)
# ============================================================

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


# ============================================================
# NEW: MECHANIC COMPLETE WITH BRAND
# ============================================================

@router.post("/{booking_id}/complete-with-brand", response_model=schemas.CompleteWithBrandResponse)
def complete_booking_with_brand(
    booking_id: int,
    payload: schemas.CompleteWithBrandRequest,
    db: Session = Depends(get_db),
    current_mechanic: models.Mechanic = Depends(get_current_mechanic),
):
    # 1. Find booking
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    # 2. Verify mechanic is assigned
    if booking.assigned_mechanic_id != current_mechanic.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Booking is not assigned to you")

    # 3. Verify booking is active
    if booking.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking is already completed or cancelled")

    # 4. Find maintenance parts linked to this service
    linked_parts = db.query(models.MaintenancePart).filter(
        models.MaintenancePart.service_id == booking.service_id,
        models.MaintenancePart.is_active == True,
    ).all()

    # 5. Check if brand selection is required
    brand_required = False
    for part in linked_parts:
        count = db.query(models.MaintenanceBrand).filter(
            models.MaintenanceBrand.part_id == part.id,
            models.MaintenanceBrand.is_active == True,
        ).count()
        if count > 0:
            brand_required = True
            break

    # 6. Brand required but not provided
    if brand_required and payload.brand_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A brand must be selected for this service")

    # 7. Validate brand if provided
    selected_brand = None
    if payload.brand_id is not None:
        selected_brand = db.query(models.MaintenanceBrand).filter(
            models.MaintenanceBrand.id == payload.brand_id,
            models.MaintenanceBrand.is_active == True,
        ).first()
        if not selected_brand:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Brand not found or inactive")

        # Verify brand belongs to a part linked to this service
        part_check = db.query(models.MaintenancePart).filter(
            models.MaintenancePart.id == selected_brand.part_id,
            models.MaintenancePart.service_id == booking.service_id,
        ).first()
        if not part_check:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Brand is not valid for this service")

    # 8. Mark booking as completed
    booking.status = "completed"
    if payload.notes:
        existing = booking.notes or ""
        separator = "\n---\n" if existing else ""
        booking.notes = f"{existing}{separator}Mechanic: {payload.notes}"

    # 9. Update car maintenance record if applicable
    maintenance_updated = False
    updated_part_name = None

    if selected_brand is not None and booking.car_id is not None:
        car = db.query(models.Car).filter(models.Car.id == booking.car_id).first()
        km_at_service = payload.current_km
        if km_at_service is None and car is not None:
            km_at_service = car.current_km

        if payload.current_km is not None and car is not None:
            car.current_km = payload.current_km

        if km_at_service is not None:
            part_for_brand = db.query(models.MaintenancePart).filter(
                models.MaintenancePart.id == selected_brand.part_id
            ).first()

            if part_for_brand is not None:
                next_change_km = km_at_service + selected_brand.interval_km

                record = db.query(models.CarMaintenance).filter(
                    models.CarMaintenance.car_id == booking.car_id,
                    models.CarMaintenance.part_id == part_for_brand.id,
                ).first()

                if not record:
                    record = models.CarMaintenance(
                        car_id=booking.car_id,
                        part_id=part_for_brand.id,
                    )
                    db.add(record)

                record.last_changed_km = km_at_service
                record.last_changed_brand_id = selected_brand.id
                record.last_changed_at = datetime.now(timezone.utc)
                record.next_change_km = next_change_km
                record.source = "service"

                maintenance_updated = True
                updated_part_name = part_for_brand.name

    db.commit()

    message = "Booking completed"
    if maintenance_updated:
        message = f"Booking completed and {updated_part_name} maintenance updated"
    elif brand_required:
        message = "Booking completed (km not set, maintenance not updated)"

    return schemas.CompleteWithBrandResponse(
        success=True,
        message=message,
        booking_id=booking.id,
        maintenance_updated=maintenance_updated,
        updated_part_name=updated_part_name,
    )