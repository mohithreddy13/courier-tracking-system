"""
parcel_service.py — CRUD operations for parcels using PyMongo.
All database calls use insert_one, find, find_one, update_one, delete_one.
"""
import uuid
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, WriteError

from database import get_db
from validation import VALID_STATUSES


def _generate_tracking_id() -> str:
    """Generate a unique tracking ID like CPT-XXXXXXXX."""
    return f"CPT-{uuid.uuid4().hex[:8].upper()}"


def _serialize(doc: dict) -> dict:
    """Convert ObjectId and datetime fields for JSON serialisation."""
    if doc is None:
        return {}
    result = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = _serialize(v)
        elif isinstance(v, list):
            result[k] = [_serialize(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result


# ══════════════════════════════════════════════════════════
#  CREATE
# ══════════════════════════════════════════════════════════
def create_parcel(data: dict) -> dict:
    """
    Insert a new parcel document.  Returns the created document (serialised).
    Raises ValueError on validation / duplicate-key errors.
    """
    db = get_db()
    now = datetime.now(timezone.utc)

    tracking_id = _generate_tracking_id()
    # Ensure uniqueness even in the unlikely collision case
    while db.parcels.find_one({"trackingId": tracking_id}):
        tracking_id = _generate_tracking_id()

    doc = {
        "trackingId":       tracking_id,
        "sender": {
            "name":    data["sender_name"],
            "phone":   data["sender_phone"],
            "address": data["sender_address"],
            "email":   data.get("sender_email", ""),
        },
        "receiver": {
            "name":    data["receiver_name"],
            "phone":   data["receiver_phone"],
            "address": data["receiver_address"],
            "email":   data.get("receiver_email", ""),
        },
        "origin":          data["origin"],
        "destination":     data["destination"],
        "weight":          float(data["weight"]),
        "deliveryCharge":  float(data["deliveryCharge"]),
        "status":          "Booked",
        "description":     data.get("description", ""),
        "bookedAt":        now,
        "estimatedDelivery": _parse_date(data.get("estimatedDelivery")),
    }

    try:
        result = db.parcels.insert_one(doc)
    except (DuplicateKeyError, WriteError) as exc:
        raise ValueError(str(exc)) from exc

    # Seed initial tracking history entry
    _insert_history(tracking_id, "Booked", data["origin"], "Parcel booked successfully", now)

    return _serialize(db.parcels.find_one({"_id": result.inserted_id}))


# ══════════════════════════════════════════════════════════
#  READ
# ══════════════════════════════════════════════════════════
def get_all_parcels(status_filter: str = "", destination_filter: str = "",
                    search: str = "") -> list[dict]:
    """Return all parcels matching optional filters."""
    db   = get_db()
    query: dict = {}

    if search:
        query["trackingId"] = {"$regex": search, "$options": "i"}
    if status_filter and status_filter != "All":
        query["status"] = status_filter
    if destination_filter and destination_filter != "All":
        query["destination"] = {"$regex": destination_filter, "$options": "i"}

    cursor = db.parcels.find(query).sort("bookedAt", -1)
    return [_serialize(doc) for doc in cursor]


def get_parcel_by_tracking_id(tracking_id: str) -> dict | None:
    """Return a single parcel by trackingId."""
    doc = get_db().parcels.find_one({"trackingId": tracking_id.upper()})
    return _serialize(doc) if doc else None


def get_parcel_by_id(parcel_id: str) -> dict | None:
    """Return a single parcel by MongoDB _id."""
    try:
        doc = get_db().parcels.find_one({"_id": ObjectId(parcel_id)})
        return _serialize(doc) if doc else None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════
#  UPDATE
# ══════════════════════════════════════════════════════════
def update_parcel(parcel_id: str, data: dict) -> dict:
    """Update editable parcel fields. Returns updated document."""
    db  = get_db()
    oid = ObjectId(parcel_id)

    update_fields = {}
    mapping = {
        "sender_name":    "sender.name",
        "sender_phone":   "sender.phone",
        "sender_address": "sender.address",
        "sender_email":   "sender.email",
        "receiver_name":  "receiver.name",
        "receiver_phone": "receiver.phone",
        "receiver_address": "receiver.address",
        "receiver_email": "receiver.email",
        "origin":         "origin",
        "destination":    "destination",
        "description":    "description",
    }
    for form_key, mongo_key in mapping.items():
        if form_key in data and data[form_key] != "":
            update_fields[mongo_key] = data[form_key]

    if "weight" in data and data["weight"]:
        update_fields["weight"] = float(data["weight"])
    if "deliveryCharge" in data and data["deliveryCharge"] != "":
        update_fields["deliveryCharge"] = float(data["deliveryCharge"])
    if "estimatedDelivery" in data and data["estimatedDelivery"]:
        update_fields["estimatedDelivery"] = _parse_date(data["estimatedDelivery"])

    if update_fields:
        db.parcels.update_one({"_id": oid}, {"$set": update_fields})

    return _serialize(db.parcels.find_one({"_id": oid}))


# ══════════════════════════════════════════════════════════
#  DELETE
# ══════════════════════════════════════════════════════════
def delete_parcel(parcel_id: str) -> bool:
    """Delete a parcel and its tracking history. Returns True on success."""
    db  = get_db()
    oid = ObjectId(parcel_id)
    doc = db.parcels.find_one({"_id": oid}, {"trackingId": 1})
    if not doc:
        return False

    tracking_id = doc["trackingId"]
    db.parcels.delete_one({"_id": oid})
    db.tracking_history.delete_many({"trackingId": tracking_id})
    return True


# ══════════════════════════════════════════════════════════
#  TRACKING HISTORY helpers
# ══════════════════════════════════════════════════════════
def _insert_history(tracking_id: str, status: str, location: str,
                    remarks: str, timestamp: datetime | None = None):
    db  = get_db()
    now = timestamp or datetime.now(timezone.utc)
    db.tracking_history.insert_one({
        "trackingId": tracking_id,
        "status":     status,
        "location":   location,
        "remarks":    remarks,
        "updatedAt":  now,
    })


def get_tracking_history(tracking_id: str) -> list[dict]:
    """Return all tracking events for a parcel, oldest first."""
    cursor = get_db().tracking_history.find(
        {"trackingId": tracking_id.upper()}
    ).sort("updatedAt", 1)
    return [_serialize(h) for h in cursor]


# ══════════════════════════════════════════════════════════
#  STATUS UPDATE (with transition validation)
# ══════════════════════════════════════════════════════════
# Allowed forward transitions (terminal states have no onward moves)
STATUS_TRANSITIONS: dict[str, list[str]] = {
    "Booked":           ["Picked Up", "Failed Delivery"],
    "Picked Up":        ["In Transit", "Failed Delivery"],
    "In Transit":       ["Out for Delivery", "Failed Delivery"],
    "Out for Delivery": ["Delivered", "Failed Delivery"],
    "Delivered":        [],
    "Failed Delivery":  ["Returned", "In Transit"],
    "Returned":         [],
}


def update_status(tracking_id: str, new_status: str,
                  location: str, remarks: str) -> dict:
    """
    Validate transition, update parcels.status and insert a tracking event.
    Returns the updated parcel document.
    """
    db  = get_db()
    tracking_id = tracking_id.upper()
    parcel = db.parcels.find_one({"trackingId": tracking_id})
    if not parcel:
        raise ValueError(f"Parcel {tracking_id} not found.")

    current = parcel["status"]
    allowed = STATUS_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        raise ValueError(
            f"Invalid transition: '{current}' → '{new_status}'. "
            f"Allowed next statuses: {allowed or ['(none — terminal status)']}"
        )

    now = datetime.now(timezone.utc)
    db.parcels.update_one(
        {"trackingId": tracking_id},
        {"$set": {"status": new_status}},
    )
    _insert_history(tracking_id, new_status, location, remarks, now)
    return _serialize(db.parcels.find_one({"trackingId": tracking_id}))


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════
def _parse_date(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def get_destinations() -> list[str]:
    return sorted(get_db().parcels.distinct("destination"))


def get_valid_statuses() -> list[str]:
    return VALID_STATUSES
