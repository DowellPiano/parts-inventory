"""Seed the database with sample parts from Schaff Piano Supply categories."""
from app import app, db
from models import Part, Bin
import random
import re
import uuid


def gen_part_number(name, category):
    cat_code = (category or 'GEN')[:3].upper()
    name_code = re.sub(r'[^A-Z0-9]', '', name.upper())[:4]
    short_id = uuid.uuid4().hex[:4].upper()
    return f"{cat_code}-{name_code}-{short_id}"


BINS = [
    {"name": "Bin A1", "shelf": "A", "row": "1", "position": "Left", "accessibility": 9},
    {"name": "Bin A2", "shelf": "A", "row": "2", "position": "Left", "accessibility": 9},
    {"name": "Bin A3", "shelf": "A", "row": "3", "position": "Center", "accessibility": 8},
    {"name": "Bin B1", "shelf": "B", "row": "1", "position": "Left", "accessibility": 7},
    {"name": "Bin B2", "shelf": "B", "row": "2", "position": "Center", "accessibility": 7},
    {"name": "Bin B3", "shelf": "B", "row": "3", "position": "Right", "accessibility": 6},
    {"name": "Bin C1", "shelf": "C", "row": "1", "position": "Left", "accessibility": 5},
    {"name": "Bin C2", "shelf": "C", "row": "2", "position": "Center", "accessibility": 4},
    {"name": "Drawer 1", "shelf": "Workbench", "row": "1", "position": "Top", "accessibility": 10},
    {"name": "Drawer 2", "shelf": "Workbench", "row": "2", "position": "Bottom", "accessibility": 8},
    {"name": "Top Shelf", "shelf": "D", "row": "1", "position": "Center", "accessibility": 2},
    {"name": "Storage Room", "shelf": "Back", "row": "1", "position": "Floor", "accessibility": 3},
]

PARTS = [
    # Hammers
    {"name": "Imadegawa Upright Hammers (Standard Bore)", "category": "Hammers", "cost": 45.00, "min_threshold": 2},
    {"name": "Abel Upright Hammers, Hornbeam (Standard Bore)", "category": "Hammers", "cost": 62.00, "min_threshold": 2},
    {"name": "Ronsen Upright Hammers (Unbored)", "category": "Hammers", "cost": 38.00, "min_threshold": 3},
    {"name": "Ronsen Grand Hammers (Unbored)", "category": "Hammers", "cost": 55.00, "min_threshold": 2},
    {"name": "Imadegawa Grand Hammers (Unbored)", "category": "Hammers", "cost": 68.00, "min_threshold": 2},
    {"name": "Abel Grand Hammers, Mahogany Moldings (Unbored)", "category": "Hammers", "cost": 85.00, "min_threshold": 1},
    {"name": "Abel Light Grand Hammers (Unbored)", "category": "Hammers", "cost": 72.00, "min_threshold": 1},
    {"name": "Hammermax Hardener Solution", "category": "Hammers", "cost": 18.50, "min_threshold": 3},

    # Hardware
    {"name": "Self Adhesive Buttons, Black (Pkg=28)", "category": "Hardware", "cost": 4.50, "min_threshold": 5},
    {"name": "Self Adhesive Buttons, Clear (Pkg=28)", "category": "Hardware", "cost": 4.50, "min_threshold": 5},
    {"name": "Cheekblock Screw", "category": "Hardware", "cost": 1.25, "min_threshold": 10},
    {"name": "Plate Pins", "category": "Hardware", "cost": 0.75, "min_threshold": 20},
    {"name": "Rubber Buttons, Brown (Pkg=10)", "category": "Hardware", "cost": 3.00, "min_threshold": 5},
    {"name": "Rubber Buttons, Black (Pkg=10)", "category": "Hardware", "cost": 3.00, "min_threshold": 5},
    {"name": "Rubber Buttons, White (Pkg=10)", "category": "Hardware", "cost": 3.00, "min_threshold": 5},
    {"name": "Rubber Bolt Caps (Pkg=10)", "category": "Hardware", "cost": 2.50, "min_threshold": 4},
    {"name": "Assortment Kit Rubber Nails And Buttons", "category": "Hardware", "cost": 24.00, "min_threshold": 1},

    # Felt & Cloth
    {"name": "Ecsaine Synthetic Buckskin", "category": "Felt & Cloth", "cost": 12.00, "min_threshold": 2},
    {"name": "English Key Bushing Cloth (By The Yard)", "category": "Felt & Cloth", "cost": 15.00, "min_threshold": 3},
    {"name": "English Key Bushing Cloth, Strips", "category": "Felt & Cloth", "cost": 8.00, "min_threshold": 5},
    {"name": "White Action Cloth", "category": "Felt & Cloth", "cost": 9.50, "min_threshold": 3},
    {"name": "Green Action Cloth", "category": "Felt & Cloth", "cost": 9.50, "min_threshold": 3},
    {"name": "Butt Felt Squares", "category": "Felt & Cloth", "cost": 6.00, "min_threshold": 4},
    {"name": "String Cover Felt (By The Yard)", "category": "Felt & Cloth", "cost": 11.00, "min_threshold": 2},
    {"name": "Grand Rim Braid, Gold", "category": "Felt & Cloth", "cost": 7.50, "min_threshold": 2},
    {"name": "Cotton Stringing Braid, Red", "category": "Felt & Cloth", "cost": 5.00, "min_threshold": 3},

    # Wire & Strings
    {"name": "Roslau Wire 1-Lb. Coils", "category": "Wire & Strings", "cost": 22.00, "min_threshold": 2},
    {"name": "Roslau Wire 5-Lb. Coils", "category": "Wire & Strings", "cost": 85.00, "min_threshold": 1},
    {"name": "Roslau Wire 1/3-Lb. Reels With Brake", "category": "Wire & Strings", "cost": 12.00, "min_threshold": 3},
    {"name": "Roslau Fine Wire", "category": "Wire & Strings", "cost": 14.00, "min_threshold": 2},
    {"name": "Mapes IGS Wire 5-Lb Coils", "category": "Wire & Strings", "cost": 78.00, "min_threshold": 1},
    {"name": "Mapes IGS Wire 1-Lb Coils", "category": "Wire & Strings", "cost": 20.00, "min_threshold": 2},
    {"name": "Music Wire Assortment Kit 1/3 Lb Reels #13-20", "category": "Wire & Strings", "cost": 95.00, "min_threshold": 1},
    {"name": "1 Lb. Wire Canister", "category": "Wire & Strings", "cost": 8.00, "min_threshold": 3},

    # Center Pins
    {"name": "Center Pins (2 Oz Pkg)", "category": "Center Pins", "cost": 6.50, "min_threshold": 5},
    {"name": "Protek Center Pin Lubricant (CLP)", "category": "Center Pins", "cost": 12.00, "min_threshold": 2},

    # Action Parts
    {"name": "Grand Repetition Spring", "category": "Action Parts", "cost": 1.50, "min_threshold": 15},
    {"name": "Upright Bridle Strap", "category": "Action Parts", "cost": 0.80, "min_threshold": 20},
    {"name": "Grand Backcheck Wire", "category": "Action Parts", "cost": 2.00, "min_threshold": 10},
    {"name": "Upright Jack Spring", "category": "Action Parts", "cost": 0.60, "min_threshold": 20},
    {"name": "Damper Felt Strip", "category": "Action Parts", "cost": 8.00, "min_threshold": 4},
    {"name": "Key Bushing Caul Set", "category": "Action Parts", "cost": 35.00, "min_threshold": 1},
]


def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create bins
        bin_objects = []
        for b in BINS:
            bin_obj = Bin(**b)
            db.session.add(bin_obj)
            bin_objects.append(bin_obj)
        db.session.flush()

        # Create parts with random stock levels and bin assignments
        for p in PARTS:
            quantity = random.randint(0, 15)
            part = Part(
                part_number=gen_part_number(p["name"], p["category"]),
                name=p["name"],
                description=f"Piano {p['category'].lower()} part from Schaff Piano Supply",
                category=p["category"],
                quantity=quantity,
                min_threshold=p["min_threshold"],
                usage_count=random.randint(0, 8),
                cost=p["cost"],
            )
            part.locations.append(random.choice(bin_objects))
            db.session.add(part)

        db.session.commit()
        print(f"Seeded {len(PARTS)} parts across {len(BINS)} bins.")


if __name__ == "__main__":
    seed()
