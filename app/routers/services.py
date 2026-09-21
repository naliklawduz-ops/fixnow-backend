from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from .. import models, schemas

router = APIRouter(
    prefix="/services",
    tags=["Services"],
)

# ============================================================
# KEYWORD MAP — Auto-link services to maintenance parts
# ============================================================

KEYWORD_PART_MAP = {
    "oil": ["Engine Oil Change", "Oil Filter"],
    "engine oil": ["Engine Oil Change", "Oil Filter"],
    "oil change": ["Engine Oil Change", "Oil Filter"],
    "oil filter": ["Oil Filter"],
    "brake": ["Brake Pads"],
    "battery": ["Battery Check"],
    "tire": ["Tire Rotation"],
    "tyre": ["Tire Rotation"],
    "wheel": ["Tire Rotation"],
    "air filter": ["Air Filter"],
    "ac filter": ["Air Filter"],
    "filter": ["Air Filter"],
}


def auto_link_parts(service: models.Service, db: Session) -> None:
    """
    Automatically link maintenance parts to a service based on keyword matching.
    Runs whenever a service is created or updated.
    """
    service_name_lower = (service.name or "").lower()
    service_category_lower = (service.category or "").lower()
    combined = f"{service_name_lower} {service_category_lower}"

    matched_part_names = set()

    for keyword, part_names in KEYWORD_PART_MAP.items():
        if keyword in combined:
            for part_name in part_names:
                matched_part_names.add(part_name)

    if not matched_part_names:
        return

    for part_name in matched_part_names:
        part = (
            db.query(models.MaintenancePart)
            .filter(models.MaintenancePart.name == part_name)
            .first()
        )
        if part and part.service_id != service.id:
            part.service_id = service.id

    db.commit()


# ============================================================
# CUSTOMER ENDPOINTS
# ============================================================

@router.get("/", response_model=List[schemas.ServiceResponse])
def get_all_services(db: Session = Depends(get_db)):
    services = db.query(models.Service).all()
    return services


@router.get("/category/{category}", response_model=List[schemas.ServiceResponse])
def get_services_by_category(category: str, db: Session = Depends(get_db)):
    services = db.query(models.Service).filter(
        models.Service.category == category
    ).all()

    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No services found for category: {category}"
        )

    return services