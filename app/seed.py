from .database import SessionLocal, engine, Base
from . import models

SERVICES_DATA = [
    {"category": "Mechanical", "name": "Oil Change", "description": "Full synthetic oil change", "price": 25000},
    {"category": "Mechanical", "name": "Engine Check", "description": "Full engine diagnostic", "price": 15000},
    {"category": "Mechanical", "name": "Brake Service", "description": "Brake pads inspection & replacement", "price": 35000},
    {"category": "Mechanical", "name": "Coolant Flush", "description": "Full coolant system flush", "price": 20000},
    {"category": "Tires", "name": "Tire Change", "description": "Replace flat or worn tire", "price": 10000},
    {"category": "Tires", "name": "Tire Rotation", "description": "Rotate all four tires", "price": 15000},
    {"category": "Tires", "name": "Wheel Alignment", "description": "Computer-aided alignment", "price": 30000},
    {"category": "Tires", "name": "Tire Pressure Check", "description": "Check and adjust tire pressure", "price": 5000},
    {"category": "Battery", "name": "Battery Replacement", "description": "New battery installation", "price": 75000},
    {"category": "Battery", "name": "Battery Jump Start", "description": "Jump start dead battery", "price": 10000},
    {"category": "Battery", "name": "Battery Check", "description": "Battery health diagnostic", "price": 8000},
    {"category": "Battery", "name": "Alternator Check", "description": "Charging system diagnostic", "price": 12000},
    {"category": "AC", "name": "AC Recharge", "description": "Refill AC refrigerant", "price": 40000},
    {"category": "AC", "name": "AC Diagnostic", "description": "Full AC system check", "price": 15000},
    {"category": "AC", "name": "AC Filter Replacement", "description": "Replace cabin air filter", "price": 20000},
    {"category": "AC", "name": "AC Compressor Repair", "description": "Compressor inspection & repair", "price": 85000},
]


def seed_services():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        existing_count = db.query(models.Service).count()
        
        if existing_count > 0:
            print(f"Database already has {existing_count} services. Skipping seed.")
            return
        
        for service_data in SERVICES_DATA:
            service = models.Service(**service_data)
            db.add(service)
        
        db.commit()
        print(f"Successfully seeded {len(SERVICES_DATA)} services.")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding services: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_services()