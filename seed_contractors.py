"""Seed default contractors - Juan and Rakia"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import get_db
from database.models import Contractor

DEFAULT_CONTRACTORS = [
    {
        "name": "Juan",
        "service_type": "General",
        "phone": "+1 253 431 2046",
        "notes": "General contractor for home repairs, handyman work. Spanish-speaking.",
        "rating": 5,
    },
    {
        "name": "Rakia Baldé",
        "service_type": "House Manager",
        "phone": "+33 7 82 82 61 45",
        "notes": "House manager/assistant. Coordinates other contractors, handles scheduling.",
        "rating": 5,
    },
]

def seed_contractors():
    with get_db() as db:
        for c in DEFAULT_CONTRACTORS:
            # Check if already exists
            existing = db.query(Contractor).filter(Contractor.name == c["name"]).first()
            if existing:
                print(f"  → {c['name']} already exists (id={existing.id})")
                continue
            
            contractor = Contractor(**c)
            db.add(contractor)
            db.flush()
            print(f"  ✓ Added {c['name']} (id={contractor.id})")
        
        db.commit()
        print("Done!")

if __name__ == "__main__":
    print("Seeding default contractors...")
    seed_contractors()
