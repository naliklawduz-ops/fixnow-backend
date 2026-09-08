from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from .. import models, schemas

router = APIRouter(
    prefix="/services",
    tags=["Services"],
)


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