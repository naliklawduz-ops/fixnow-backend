from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from ..database import get_db
from ..models import (
    MaintenancePart,
    MaintenanceBrand,
    CarMaintenance,
    Car,
    Service,
    User,
)
from ..schemas import (
    MaintenancePartCreate,
    MaintenancePartUpdate,
    MaintenancePartResponse,
    MaintenanceBrandCreate,
    MaintenanceBrandUpdate,
    MaintenanceBrandResponse,
    MaintenanceItemStatus,
    CarMaintenanceSummary,
    CarMaintenanceResetRequest,
)
from ..auth_utils import get_current_user, get_current_admin


router = APIRouter(tags=["maintenance"])


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _calculate_status(km_remaining: Optional[int]) -> str:
    """
    Determine color status based on km remaining until next change.
    - unknown: no current_km or no next_change_km
    - red: overdue (km_remaining <= 0)
    - yellow: within 1000 km
    - green: more than 1000 km
    """
    if km_remaining is None:
        return "unknown"
    if km_remaining <= 0:
        return "red"
    if km_remaining <= 1000:
        return "yellow"
    return "green"


def _estimate_months_remaining(
    km_remaining: Optional[int], km_per_month: Optional[int]
) -> Optional[float]:
    """Estimate months until next change based on driving habits."""
    if km_remaining is None or not km_per_month or km_per_month <= 0:
        return None
    if km_remaining <= 0:
        return 0.0
    return round(km_remaining / km_per_month, 1)


def _build_item_status(
    part: MaintenancePart,
    car: Car,
    record: Optional[CarMaintenance],
    db: Session,
) -> MaintenanceItemStatus:
    """Build a single maintenance item status from part + car + record."""
    # Get all active brands for this part
    brands = (
        db.query(MaintenanceBrand)
        .filter(
            MaintenanceBrand.part_id == part.id,
            MaintenanceBrand.is_active == True,
        )
        .order_by(MaintenanceBrand.interval_km.asc())
        .all()
    )
    brand_responses = [MaintenanceBrandResponse.model_validate(b) for b in brands]

    # If no record exists, part is unknown (customer hasn't set anything)
    if not record or record.last_changed_km is None:
        return MaintenanceItemStatus(
            part_id=part.id,
            part_name=part.name,
            last_changed_km=None,
            last_changed_at=None,
            last_changed_brand_id=None,
            last_changed_brand_name=None,
            next_change_km=None,
            km_remaining=None,
            status="unknown",
            source=None,
            service_id=part.service_id,
            service_category=part.service.category if part.service else None,
            estimated_months_remaining=None,
            available_brands=brand_responses,
        )

    # Calculate km remaining
    current_km = car.current_km
    next_change_km = record.next_change_km

    km_remaining = None
    if current_km is not None and next_change_km is not None:
        km_remaining = next_change_km - current_km

    item_status = _calculate_status(km_remaining)

    # Get brand name if brand_id is set
    brand_name = None
    if record.last_changed_brand_id:
        brand = (
            db.query(MaintenanceBrand)
            .filter(MaintenanceBrand.id == record.last_changed_brand_id)
            .first()
        )
        if brand:
            brand_name = brand.brand_name

    months_remaining = _estimate_months_remaining(
        km_remaining, car.estimated_km_per_month
    )

    return MaintenanceItemStatus(
        part_id=part.id,
        part_name=part.name,
        last_changed_km=record.last_changed_km,
        last_changed_at=record.last_changed_at,
        last_changed_brand_id=record.last_changed_brand_id,
        last_changed_brand_name=brand_name,
        next_change_km=next_change_km,
        km_remaining=km_remaining,
        status=item_status,
        source=record.source,
        service_id=part.service_id,
        service_category=part.service.category if part.service else None,
        estimated_months_remaining=months_remaining,
        available_brands=brand_responses,
    )


def _get_car_or_404(car_id: int, user_id: int, db: Session) -> Car:
    """Fetch car and verify it belongs to the user."""
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Car not found",
        )
    if car.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Car does not belong to you",
        )
    return car


# ============================================================
# ADMIN ENDPOINTS — PARTS
# ============================================================

@router.get("/admin/maintenance/parts", response_model=List[MaintenancePartResponse])
def admin_list_parts(
    include_inactive: bool = False,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all maintenance parts (admin only)."""
    query = db.query(MaintenancePart)
    if not include_inactive:
        query = query.filter(MaintenancePart.is_active == True)
    parts = query.order_by(MaintenancePart.id.asc()).all()

    result = []
    for part in parts:
        brands = (
            db.query(MaintenanceBrand)
            .filter(
                MaintenanceBrand.part_id == part.id,
                MaintenanceBrand.is_active == True,
            )
            .order_by(MaintenanceBrand.interval_km.asc())
            .all()
        )
        part_dict = MaintenancePartResponse.model_validate(part)
        part_dict.brands = [MaintenanceBrandResponse.model_validate(b) for b in brands]
        result.append(part_dict)
    return result


@router.post(
    "/admin/maintenance/parts",
    response_model=MaintenancePartResponse,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_part(
    payload: MaintenancePartCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new maintenance part (admin only)."""
    # Validate service_id if provided
    if payload.service_id is not None:
        service = db.query(Service).filter(Service.id == payload.service_id).first()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service not found",
            )

    part = MaintenancePart(
        name=payload.name,
        default_interval_km=payload.default_interval_km,
        service_id=payload.service_id,
        is_active=payload.is_active,
    )
    db.add(part)
    db.commit()
    db.refresh(part)

    response = MaintenancePartResponse.model_validate(part)
    response.brands = []
    return response


@router.put(
    "/admin/maintenance/parts/{part_id}",
    response_model=MaintenancePartResponse,
)
def admin_update_part(
    part_id: int,
    payload: MaintenancePartUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update a maintenance part (admin only)."""
    part = db.query(MaintenancePart).filter(MaintenancePart.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )

    if payload.name is not None:
        part.name = payload.name
    if payload.default_interval_km is not None:
        part.default_interval_km = payload.default_interval_km
    if payload.service_id is not None:
        # Allow setting to None explicitly via a special flag or just skip for now
        if payload.service_id > 0:
            service = db.query(Service).filter(Service.id == payload.service_id).first()
            if not service:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Service not found",
                )
            part.service_id = payload.service_id
    if payload.is_active is not None:
        part.is_active = payload.is_active

    db.commit()
    db.refresh(part)

    brands = (
        db.query(MaintenanceBrand)
        .filter(
            MaintenanceBrand.part_id == part.id,
            MaintenanceBrand.is_active == True,
        )
        .order_by(MaintenanceBrand.interval_km.asc())
        .all()
    )
    response = MaintenancePartResponse.model_validate(part)
    response.brands = [MaintenanceBrandResponse.model_validate(b) for b in brands]
    return response


@router.delete("/admin/maintenance/parts/{part_id}")
def admin_soft_delete_part(
    part_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Soft-delete a maintenance part (admin only)."""
    part = db.query(MaintenancePart).filter(MaintenancePart.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )

    part.is_active = False
    # Also deactivate its brands
    db.query(MaintenanceBrand).filter(
        MaintenanceBrand.part_id == part.id
    ).update({"is_active": False})
    db.commit()

    return {"success": True, "message": "Part deactivated"}


# ============================================================
# ADMIN ENDPOINTS — BRANDS
# ============================================================

@router.get(
    "/admin/maintenance/brands",
    response_model=List[MaintenanceBrandResponse],
)
def admin_list_brands(
    part_id: Optional[int] = None,
    include_inactive: bool = False,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all maintenance brands, optionally filtered by part (admin only)."""
    query = db.query(MaintenanceBrand)
    if part_id is not None:
        query = query.filter(MaintenanceBrand.part_id == part_id)
    if not include_inactive:
        query = query.filter(MaintenanceBrand.is_active == True)
    brands = query.order_by(MaintenanceBrand.part_id.asc(), MaintenanceBrand.interval_km.asc()).all()
    return [MaintenanceBrandResponse.model_validate(b) for b in brands]


@router.post(
    "/admin/maintenance/brands",
    response_model=MaintenanceBrandResponse,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_brand(
    payload: MaintenanceBrandCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new maintenance brand (admin only)."""
    part = db.query(MaintenancePart).filter(MaintenancePart.id == payload.part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Part not found",
        )

    brand = MaintenanceBrand(
        part_id=payload.part_id,
        brand_name=payload.brand_name,
        interval_km=payload.interval_km,
        is_active=payload.is_active,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return MaintenanceBrandResponse.model_validate(brand)


@router.put(
    "/admin/maintenance/brands/{brand_id}",
    response_model=MaintenanceBrandResponse,
)
def admin_update_brand(
    brand_id: int,
    payload: MaintenanceBrandUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update a maintenance brand (admin only)."""
    brand = db.query(MaintenanceBrand).filter(MaintenanceBrand.id == brand_id).first()
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found",
        )

    if payload.brand_name is not None:
        brand.brand_name = payload.brand_name
    if payload.interval_km is not None:
        brand.interval_km = payload.interval_km
    if payload.is_active is not None:
        brand.is_active = payload.is_active

    db.commit()
    db.refresh(brand)
    return MaintenanceBrandResponse.model_validate(brand)


@router.delete("/admin/maintenance/brands/{brand_id}")
def admin_soft_delete_brand(
    brand_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Soft-delete a maintenance brand (admin only)."""
    brand = db.query(MaintenanceBrand).filter(MaintenanceBrand.id == brand_id).first()
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found",
        )

    brand.is_active = False
    db.commit()
    return {"success": True, "message": "Brand deactivated"}


# ============================================================
# CUSTOMER ENDPOINTS
# ============================================================

@router.get(
    "/cars/{car_id}/maintenance",
    response_model=CarMaintenanceSummary,
)
def get_car_maintenance(
    car_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full maintenance status for a car (customer only)."""
    car = _get_car_or_404(car_id, current_user.id, db)

    # Get all active parts
    parts = (
        db.query(MaintenancePart)
        .filter(MaintenancePart.is_active == True)
        .order_by(MaintenancePart.id.asc())
        .all()
    )

    # Get existing maintenance records for this car
    records = (
        db.query(CarMaintenance)
        .filter(CarMaintenance.car_id == car_id)
        .all()
    )
    records_by_part = {r.part_id: r for r in records}

    # Build item statuses
    items = []
    for part in parts:
        record = records_by_part.get(part.id)
        items.append(_build_item_status(part, car, record, db))

    # Sort: red → yellow → unknown → green
    status_order = {"red": 0, "yellow": 1, "unknown": 2, "green": 3}
    items.sort(key=lambda i: (status_order.get(i.status, 99), i.part_name))

    # Count statuses
    red_count = sum(1 for i in items if i.status == "red")
    yellow_count = sum(1 for i in items if i.status == "yellow")
    green_count = sum(1 for i in items if i.status == "green")

    return CarMaintenanceSummary(
        car_id=car.id,
        car_name=f"{car.brand} {car.model} {car.year}",
        current_km=car.current_km,
        estimated_km_per_month=car.estimated_km_per_month,
        total_parts=len(items),
        red_count=red_count,
        yellow_count=yellow_count,
        green_count=green_count,
        items=items,
    )


@router.put("/cars/{car_id}/km")
def update_car_km(
    car_id: int,
    payload: dict,  # { current_km: int, estimated_km_per_month?: int }
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update car's current km and optionally estimated km per month."""
    car = _get_car_or_404(car_id, current_user.id, db)

    if "current_km" in payload:
        try:
            km = int(payload["current_km"])
            if km < 0:
                raise ValueError
            car.current_km = km
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="current_km must be a non-negative integer",
            )

    if "estimated_km_per_month" in payload and payload["estimated_km_per_month"] is not None:
        try:
            est = int(payload["estimated_km_per_month"])
            if est < 0:
                raise ValueError
            car.estimated_km_per_month = est
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="estimated_km_per_month must be a non-negative integer",
            )

    db.commit()
    db.refresh(car)

    return {
        "success": True,
        "message": "Car km updated",
        "current_km": car.current_km,
        "estimated_km_per_month": car.estimated_km_per_month,
    }


@router.post("/cars/{car_id}/maintenance/{part_id}/reset")
def reset_car_maintenance(
    car_id: int,
    part_id: int,
    payload: CarMaintenanceResetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Customer manually marks a part as changed."""
    car = _get_car_or_404(car_id, current_user.id, db)

    part = db.query(MaintenancePart).filter(MaintenancePart.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Part not found",
        )

    # Determine interval to use
    interval_km = part.default_interval_km
    if payload.brand_id is not None:
        brand = (
            db.query(MaintenanceBrand)
            .filter(
                MaintenanceBrand.id == payload.brand_id,
                MaintenanceBrand.part_id == part.id,
            )
            .first()
        )
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Brand not found for this part",
            )
        interval_km = brand.interval_km

    next_change_km = payload.last_changed_km + interval_km

    # Find or create record
    record = (
        db.query(CarMaintenance)
        .filter(
            CarMaintenance.car_id == car_id,
            CarMaintenance.part_id == part_id,
        )
        .first()
    )

    if not record:
        record = CarMaintenance(car_id=car_id, part_id=part_id)
        db.add(record)

    record.last_changed_km = payload.last_changed_km
    record.last_changed_brand_id = payload.brand_id
    record.last_changed_at = datetime.now(timezone.utc)
    record.next_change_km = next_change_km
    record.source = "manual"

    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "message": f"{part.name} marked as changed",
        "part_id": part.id,
        "part_name": part.name,
        "last_changed_km": record.last_changed_km,
        "next_change_km": record.next_change_km,
    }