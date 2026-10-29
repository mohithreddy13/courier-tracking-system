"""
validation.py — MongoDB $jsonSchema validators applied via PyMongo.
Run this module once before starting the application (or call
`setup_collections()` from app.py on startup).
"""
from pymongo import ASCENDING
from pymongo.errors import CollectionInvalid, OperationFailure
from database import get_db

# ─────────────────────────────────────────────
#  Valid status values (single source of truth)
# ─────────────────────────────────────────────
VALID_STATUSES = [
    "Booked",
    "Picked Up",
    "In Transit",
    "Out for Delivery",
    "Delivered",
    "Failed Delivery",
    "Returned",
]

# ─────────────────────────────────────────────
#  $jsonSchema for parcels
# ─────────────────────────────────────────────
PARCELS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "trackingId", "sender", "receiver",
            "origin", "destination",
            "weight", "deliveryCharge",
            "status", "bookedAt",
        ],
        "properties": {
            "trackingId": {
                "bsonType": "string",
                "description": "Unique parcel tracking ID — required string",
            },
            "sender": {
                "bsonType": "object",
                "required": ["name", "phone", "address"],
                "properties": {
                    "name":    {"bsonType": "string"},
                    "phone":   {"bsonType": "string"},
                    "address": {"bsonType": "string"},
                    "email":   {"bsonType": "string"},
                },
            },
            "receiver": {
                "bsonType": "object",
                "required": ["name", "phone", "address"],
                "properties": {
                    "name":    {"bsonType": "string"},
                    "phone":   {"bsonType": "string"},
                    "address": {"bsonType": "string"},
                    "email":   {"bsonType": "string"},
                },
            },
            "origin":          {"bsonType": "string"},
            "destination":     {"bsonType": "string"},
            "weight": {
                "bsonType": ["double", "int"],
                "minimum": 0.01,
                "description": "Weight in kg — must be positive",
            },
            "deliveryCharge": {
                "bsonType": ["double", "int"],
                "minimum": 0,
                "description": "Delivery charge in INR — non-negative",
            },
            "status": {
                "bsonType": "string",
                "enum": VALID_STATUSES,
                "description": "Current parcel status",
            },
            "bookedAt": {
                "bsonType": "date",
                "description": "Booking timestamp",
            },
            "estimatedDelivery": {
                "bsonType": "date",
                "description": "Estimated delivery date (optional)",
            },
            "description": {"bsonType": "string"},
        },
    }
}

# ─────────────────────────────────────────────
#  $jsonSchema for tracking_history
# ─────────────────────────────────────────────
TRACKING_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["trackingId", "status", "location", "updatedAt"],
        "properties": {
            "trackingId": {"bsonType": "string"},
            "status":     {"bsonType": "string", "enum": VALID_STATUSES},
            "location":   {"bsonType": "string"},
            "remarks":    {"bsonType": "string"},
            "updatedAt":  {"bsonType": "date"},
        },
    }
}


def _create_or_update_collection(db, name: str, validator: dict):
    """Create collection with validator, or update validator if it exists."""
    existing = db.list_collection_names()
    if name not in existing:
        db.create_collection(name, validator=validator, validationLevel="strict")
        print(f"  [+] Created collection '{name}' with $jsonSchema validator.")
    else:
        try:
            db.command("collMod", name, validator=validator, validationLevel="strict")
            print(f"  [~] Updated validator on existing collection '{name}'.")
        except OperationFailure as e:
            print(f"  [!] Could not update validator for '{name}': {e}")


def setup_collections():
    """
    Initialise the courier_tracking database:
    - Create / update parcels and tracking_history with $jsonSchema validators.
    - Create PyMongo indexes (unique trackingId, status, destination, compound).
    - These indexes also satisfy the PyMongo indexing requirement; the
      node_indexing/ module creates the *same* indexes via the Node.js driver
      for the explicit Node.js indexing demonstration.
    """
    db = get_db()

    print("Setting up MongoDB collections and validators …")
    _create_or_update_collection(db, "parcels",          PARCELS_VALIDATOR)
    _create_or_update_collection(db, "tracking_history", TRACKING_VALIDATOR)

    # ── PyMongo index creation ────────────────────────────────────────────────
    parcels_col  = db["parcels"]
    history_col  = db["tracking_history"]

    parcels_col.create_index("trackingId", unique=True,  name="idx_trackingId_unique")
    parcels_col.create_index("status",                   name="idx_status")
    parcels_col.create_index("destination",              name="idx_destination")
    parcels_col.create_index("bookedAt",                 name="idx_bookedAt")
    history_col.create_index(
        [("trackingId", ASCENDING), ("updatedAt", ASCENDING)],
        name="idx_trackingId_updatedAt_compound",
    )
    print("  [+] Indexes created / confirmed via PyMongo.")
    print("Setup complete.\n")


if __name__ == "__main__":
    setup_collections()
