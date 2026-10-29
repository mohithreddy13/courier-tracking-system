"""
seed_data.py — Insert 80 fictional parcel records + tracking history
into the courier_tracking database using PyMongo.

Safe for multiple runs: checks existing trackingIds before inserting.
"""
import random
from datetime import datetime, timezone, timedelta
from database import get_db
from validation import setup_collections, VALID_STATUSES

# ── Sample data pools ─────────────────────────────────────
CITIES = [
    "Ludhiana", "Delhi", "Mumbai", "Hyderabad", "Bengaluru",
    "Chennai", "Kolkata", "Pune", "Ahmedabad", "Jaipur",
    "Surat", "Lucknow", "Kanpur", "Nagpur", "Indore",
    "Bhopal", "Visakhapatnam", "Patna", "Vadodara", "Ghaziabad",
]

SENDER_NAMES = [
    "Rajesh Kumar", "Priya Sharma", "Amit Singh", "Sunita Patel",
    "Vikram Mehta", "Anjali Gupta", "Rohit Verma", "Neha Joshi",
    "Arjun Nair", "Kavya Reddy", "Sanjay Yadav", "Meena Iyer",
    "Deepak Pillai", "Pooja Bhatt", "Rahul Mishra",
]

RECEIVER_NAMES = [
    "Suresh Babu", "Lakshmi Devi", "Manoj Tiwari", "Rekha Agarwal",
    "Harish Rao", "Usha Krishnan", "Ganesh Mukherjee", "Anita Das",
    "Vinod Sinha", "Sarla Choudhary", "Ramesh Chandra", "Geeta Nair",
    "Prakash Menon", "Savitri Iyer", "Kuldeep Chauhan",
]

DESCRIPTIONS = [
    "Electronics — Laptop", "Clothing and Textiles", "Medical Supplies",
    "Books and Stationery", "Jewellery", "Auto Parts", "Household Items",
    "Food Products", "Cosmetics", "Sports Equipment", "Industrial Tools",
    "Documents", "Fragile — Glassware", "Mobile Phone", "Computer Parts",
]


def _random_phone() -> str:
    return f"+91{random.randint(7000000000, 9999999999)}"


def _random_date(start_days_ago: int = 180, end_days_ago: int = 0) -> datetime:
    delta = random.randint(end_days_ago, start_days_ago)
    return datetime.now(timezone.utc) - timedelta(days=delta)


STATUS_FLOW = [
    "Booked", "Picked Up", "In Transit",
    "Out for Delivery", "Delivered",
]

TERMINAL_FAILURES = ["Failed Delivery", "Returned"]


def _build_status_chain(booked_at: datetime) -> list[tuple[str, datetime]]:
    """Return a list of (status, timestamp) pairs for a realistic journey."""
    choice = random.random()
    events: list[tuple[str, datetime]] = [("Booked", booked_at)]

    if choice < 0.60:
        # Happy path — fully delivered
        steps = STATUS_FLOW[1:]
    elif choice < 0.75:
        # In transit
        steps = STATUS_FLOW[1:3]
    elif choice < 0.85:
        # Out for delivery, then failed
        steps = [*STATUS_FLOW[1:4], "Failed Delivery"]
    elif choice < 0.92:
        # Failed then returned
        steps = [STATUS_FLOW[1], STATUS_FLOW[2], "Failed Delivery", "Returned"]
    else:
        # Just picked up
        steps = STATUS_FLOW[1:2]

    current_time = booked_at
    for status in steps:
        current_time = current_time + timedelta(hours=random.randint(12, 48))
        events.append((status, current_time))

    return events


def seed():
    setup_collections()
    db = get_db()
    existing_ids = set(db.parcels.distinct("trackingId"))

    inserted_parcels = 0
    inserted_history = 0
    counter = 1

    while inserted_parcels < 80:
        tracking_id = f"CPT-{counter:08d}"
        counter += 1

        if tracking_id in existing_ids:
            continue

        origin      = random.choice(CITIES)
        destination = random.choice([c for c in CITIES if c != origin])
        booked_at   = _random_date(180, 0)
        est_days    = random.randint(2, 7)
        est_delivery = booked_at + timedelta(days=est_days)
        weight      = round(random.uniform(0.1, 30.0), 2)
        charge      = round(weight * random.uniform(40, 120), 2)

        status_chain = _build_status_chain(booked_at)
        final_status = status_chain[-1][0]

        sender_name   = random.choice(SENDER_NAMES)
        receiver_name = random.choice(RECEIVER_NAMES)

        parcel = {
            "trackingId": tracking_id,
            "sender": {
                "name":    sender_name,
                "phone":   _random_phone(),
                "address": f"{random.randint(1,999)}, {origin} - {random.randint(100000,999999)}",
                "email":   f"{sender_name.lower().replace(' ', '.')}@example.com",
            },
            "receiver": {
                "name":    receiver_name,
                "phone":   _random_phone(),
                "address": f"{random.randint(1,999)}, {destination} - {random.randint(100000,999999)}",
                "email":   f"{receiver_name.lower().replace(' ', '.')}@example.com",
            },
            "origin":          origin,
            "destination":     destination,
            "weight":          weight,
            "deliveryCharge":  charge,
            "status":          final_status,
            "description":     random.choice(DESCRIPTIONS),
            "bookedAt":        booked_at,
            "estimatedDelivery": est_delivery,
        }

        try:
            db.parcels.insert_one(parcel)
            inserted_parcels += 1
            existing_ids.add(tracking_id)
        except Exception as exc:
            print(f"  [!] Skipped {tracking_id}: {exc}")
            continue

        # Insert all tracking history events for this parcel
        cities_visited = [origin]
        for idx, (status, ts) in enumerate(status_chain):
            if idx == 0:
                location = origin
                remarks  = "Parcel booked and registered at origin."
            elif status == "Picked Up":
                location = origin
                remarks  = f"Parcel picked up from sender in {origin}."
            elif status == "In Transit":
                hub = random.choice([c for c in CITIES if c not in (origin, destination)])
                cities_visited.append(hub)
                location = hub
                remarks  = f"Parcel in transit through {hub} hub."
            elif status == "Out for Delivery":
                location = destination
                remarks  = f"Out for delivery in {destination}."
            elif status == "Delivered":
                location = destination
                remarks  = f"Delivered successfully to {receiver_name} in {destination}."
            elif status == "Failed Delivery":
                location = destination
                remarks  = "Delivery attempt failed — recipient unavailable."
            elif status == "Returned":
                location = origin
                remarks  = "Parcel returned to sender."
            else:
                location = destination
                remarks  = ""

            try:
                db.tracking_history.insert_one({
                    "trackingId": tracking_id,
                    "status":     status,
                    "location":   location,
                    "remarks":    remarks,
                    "updatedAt":  ts,
                })
                inserted_history += 1
            except Exception as exc:
                print(f"  [!] History insert error for {tracking_id}: {exc}")

    print(f"\nSeed complete: {inserted_parcels} parcels, {inserted_history} tracking events inserted.")


if __name__ == "__main__":
    seed()
