"""
Seed script for FixNow Maintenance Tracker.

Run standalone:
    python -m app.seed_maintenance

Idempotent — safe to run multiple times. Skips anything already in the DB.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone

from .database import SessionLocal, engine, Base
from .models import (
    MaintenancePart,
    MaintenanceBrand,
    Service,
)


# ============================================================
# SEED DATA
# ============================================================

PARTS_DATA = [
    {
        "name": "Engine Oil Change",
        "default_interval_km": 5000,
        "service_match_keywords": ["oil change", "engine oil", "oil"],
    },
    {
        "name": "Oil Filter",
        "default_interval_km": 5000,
        "service_match_keywords": ["oil change", "oil filter", "oil"],
    },
    {
        "name": "Air Filter",
        "default_interval_km": 15000,
        "service_match_keywords": ["air filter", "filter"],
    },
    {
        "name": "Brake Pads",
        "default_interval_km": 20000,
        "service_match_keywords": ["brake"],
    },
    {
        "name": "Battery Check",
        "default_interval_km": 30000,
        "service_match_keywords": ["battery"],
    },
    {
        "name": "Tire Rotation",
        "default_interval_km": 10000,
        "service_match_keywords": ["tire", "tyre", "wheel"],
    },
]


BRANDS_DATA = {
    "Engine Oil Change": [
        {"brand_name": "Castrol", "interval_km": 5000},
        {"brand_name": "Mobil 1", "interval_km": 5000},
        {"brand_name": "Shell Helix", "interval_km": 5000},
        {"brand_name": "Total", "interval_km": 5000},
        {"brand_name": "Liqui-Moly", "interval_km": 5000},
    ],
    "Oil Filter": [
        {"brand_name": "Mann", "interval_km": 5000},
        {"brand_name": "Bosch", "interval_km": 5000},
        {"brand_name": "Mahle", "interval_km": 5000},
    ],
    "Air Filter": [
        {"brand_name": "Mann", "interval_km": 15000},
        {"brand_name": "Bosch", "interval_km": 15000},
        {"brand_name": "K&N", "interval_km": 15000},
    ],
    "Brake Pads": [
        {"brand_name": "Brembo", "interval_km": 20000},
        {"brand_name": "Bosch", "interval_km": 20000},
        {"brand_name": "TRW", "interval_km": 20000},
    ],
    "Battery Check": [
        {"brand_name": "Varta", "interval_km": 30000},
        {"brand_name": "Bosch", "interval_km": 30000},
        {"brand_name": "Exide", "interval_km": 30000},
    ],
    "Tire Rotation": [
        {"brand_name": "Michelin", "interval_km": 10000},
        {"brand_name": "Bridgestone", "interval_km": 10000},
        {"brand_name": "Pirelli", "interval_km": 10000},
    ],
}


# ============================================================
# HELPERS
# ============================================================

def _find_matching_service(db: Session, keywords: list) -> Service | None:
    """Find the first service whose name matches any keyword (case-insensitive)."""
    services = db.query(Service).all()
    for service in services:
        service_name_lower = (service.name or "").lower()
        for keyword in keywords:
            if keyword.lower() in service_name_lower:
                return service
    return None


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ============================================================
# SEED FUNCTIONS
# ============================================================

def seed_parts(db: Session) -> dict:
    """
    Seed maintenance parts.
    Returns a dict: { part_name: MaintenancePart instance }
    """
    _print_header("SEEDING MAINTENANCE PARTS")
    parts_by_name = {}

    for part_data in PARTS_DATA:
        name = part_data["name"]
        interval = part_data["default_interval_km"]
        keywords = part_data["service_match_keywords"]

        existing = (
            db.query(MaintenancePart)
            .filter(MaintenancePart.name == name)
            .first()
        )
        if existing:
            print(f"  [SKIP]     Part already exists: {name} (id={existing.id})")
            parts_by_name[name] = existing
            continue

        service = _find_matching_service(db, keywords)
        service_id = service.id if service else None
        service_label = f"{service.name} (id={service.id})" if service else "no match"

        part = MaintenancePart(
            name=name,
            default_interval_km=interval,
            service_id=service_id,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(part)
        db.flush()

        print(f"  [INSERTED] Part: {name} | interval={interval} km | service={service_label}")
        parts_by_name[name] = part

    db.commit()
    return parts_by_name


def seed_brands(db: Session, parts_by_name: dict) -> None:
    """Seed maintenance brands linked to parts."""
    _print_header("SEEDING MAINTENANCE BRANDS")

    for part_name, brands in BRANDS_DATA.items():
        part = parts_by_name.get(part_name)
        if part is None:
            print(f"  [SKIP]     Part not found for brands: {part_name}")
            continue

        print(f"\n  Part: {part_name} (id={part.id})")

        for brand_data in brands:
            brand_name = brand_data["brand_name"]
            interval_km = brand_data["interval_km"]

            existing = (
                db.query(MaintenanceBrand)
                .filter(
                    MaintenanceBrand.part_id == part.id,
                    MaintenanceBrand.brand_name == brand_name,
                )
                .first()
            )
            if existing:
                print(f"    [SKIP]     Brand already exists: {brand_name}")
                continue

            brand = MaintenanceBrand(
                part_id=part.id,
                brand_name=brand_name,
                interval_km=interval_km,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(brand)
            print(f"    [INSERTED] Brand: {brand_name} | interval={interval_km} km")

    db.commit()


# ============================================================
# MAIN
# ============================================================

def run_seed() -> None:
    print()
    print("############################################################")
    print("#                                                          #")
    print("#   FIXNOW MAINTENANCE TRACKER — SEED SCRIPT               #")
    print("#                                                          #")
    print("############################################################")

    # Ensure tables exist (idempotent — create_all skips existing)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        parts_by_name = seed_parts(db)
        seed_brands(db, parts_by_name)

        _print_header("SEED COMPLETE")
        total_parts = db.query(MaintenancePart).count()
        total_brands = db.query(MaintenanceBrand).count()
        print(f"  Total parts in DB:  {total_parts}")
        print(f"  Total brands in DB: {total_brands}")
        print()

    except Exception as e:
        db.rollback()
        print()
        print(f"  ❌ ERROR: {e}")
        print()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()