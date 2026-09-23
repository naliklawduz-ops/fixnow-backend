from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    address = Column(String, nullable=True)
    fcm_token = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cars = relationship("Car", back_populates="owner", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="customer", cascade="all, delete-orphan")


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    color = Column(String, nullable=False)
    plate = Column(String, nullable=False)
    current_km = Column(Integer, nullable=True)
    estimated_km_per_month = Column(Integer, nullable=True, default=1000)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="cars")
    maintenance_records = relationship(
        "CarMaintenance", back_populates="car", cascade="all, delete-orphan"
    )


class ServiceCategory(Base):
    __tablename__ = "service_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    icon = Column(String, nullable=True, default="🔧")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Integer, nullable=False)

    maintenance_parts = relationship("MaintenancePart", back_populates="service")


class Mechanic(Base):
    __tablename__ = "mechanics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    rating = Column(Float, default=5.0)
    is_available = Column(Boolean, default=True)
    access_code = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    fcm_token = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bookings = relationship("Booking", back_populates="mechanic")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    car_id = Column(Integer, ForeignKey("cars.id"), nullable=True)
    assigned_mechanic_id = Column(Integer, ForeignKey("mechanics.id"), nullable=True)
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    address = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("User", back_populates="bookings")
    service = relationship("Service")
    car = relationship("Car")
    mechanic = relationship("Mechanic", back_populates="bookings")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    sender_type = Column(String, nullable=False)
    sender_name = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MaintenancePart(Base):
    __tablename__ = "maintenance_parts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    default_interval_km = Column(Integer, nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    service = relationship("Service", back_populates="maintenance_parts")
    brands = relationship(
        "MaintenanceBrand", back_populates="part", cascade="all, delete-orphan"
    )
    car_records = relationship("CarMaintenance", back_populates="part")


class MaintenanceBrand(Base):
    __tablename__ = "maintenance_brands"

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("maintenance_parts.id", ondelete="CASCADE"), nullable=False)
    brand_name = Column(String, nullable=False)
    interval_km = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    part = relationship("MaintenancePart", back_populates="brands")


class CarMaintenance(Base):
    __tablename__ = "car_maintenance"

    id = Column(Integer, primary_key=True, index=True)
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="CASCADE"), nullable=False)
    part_id = Column(Integer, ForeignKey("maintenance_parts.id"), nullable=False)
    last_changed_km = Column(Integer, nullable=True)
    last_changed_brand_id = Column(Integer, ForeignKey("maintenance_brands.id"), nullable=True)
    last_changed_at = Column(DateTime(timezone=True), nullable=True)
    next_change_km = Column(Integer, nullable=True)
    source = Column(String, nullable=False, default="manual")
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    car = relationship("Car", back_populates="maintenance_records")
    part = relationship("MaintenancePart", back_populates="car_records")
    brand = relationship("MaintenanceBrand")


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
