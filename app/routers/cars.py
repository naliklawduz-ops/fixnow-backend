from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..auth_utils import get_current_user_id

router = APIRouter(
    prefix="/cars",
    tags=["Cars"],
)


@router.post("/", response_model=schemas.CarResponse, status_code=status.HTTP_201_CREATED)
def add_car(
    car_data: schemas.CarCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    new_car = models.Car(
        user_id=user_id,
        brand=car_data.brand,
        model=car_data.model,
        year=car_data.year,
        color=car_data.color,
        plate=car_data.plate,
    )
    
    db.add(new_car)
    db.commit()
    db.refresh(new_car)
    
    return new_car


@router.get("/", response_model=List[schemas.CarResponse])
def get_cars(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    cars = db.query(models.Car).filter(models.Car.user_id == user_id).all()
    return cars


@router.delete("/{car_id}")
def delete_car(
    car_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    car = db.query(models.Car).filter(
        models.Car.id == car_id,
        models.Car.user_id == user_id,
    ).first()
    
    if not car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Car not found"
        )
    
    db.delete(car)
    db.commit()
    
    return {"success": True, "message": "Car deleted successfully"}