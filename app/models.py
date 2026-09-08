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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="cars")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Integer, nullable=False)


class Mechanic(Base):
    __tablename__ = "mechanics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    rating = Column(Float, default=5.0)
    is_available = Column(Boolean, default=True)
    access_code = Column(String, nullable=False)  # NEW
    is_active = Column(Boolean, default=True)  # NEW
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bookings = relationship("Booking", back_populates="mechanic")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    car_id = Column(Integer, ForeignKey("cars.id"), nullable=True)
    assigned_mechanic_id = Column(Integer, ForeignKey("mechanics.id"), nullable=True)  # NEW
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    address = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")  # active, completed, cancelled
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
    sender_type = Column(String, nullable=False)  # "customer" or "mechanic"
    sender_name = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())