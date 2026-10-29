"""
test_evidence.py — Testing evidence for CRUD, duplicate IDs,
invalid documents, and status updates.
"""
from database import get_db
from pymongo.errors import DuplicateKeyError, WriteError
from datetime import datetime, timezone

db = get_db()

print("=" * 60)
print("  TESTING EVIDENCE — COURIER TRACKING SYSTEM")
print("=" * 60)

# ── TEST 1: CREATE ────────────────────────────────────────────
print("\nTEST 1: CREATE — Insert a new parcel")
print("-" * 40)
db.parcels.delete_one({"trackingId": "CPT-TEST-001"})
new_parcel = {
    "trackingId": "CPT-TEST-001",
    "sender":   {"name": "Test Sender",   "phone": "+919000000001", "address": "1, Delhi - 110001",  "email": "sender@test.com"},
    "receiver": {"name": "Test Receiver", "phone": "+919000000002", "address": "2, Mumbai - 400001", "email": "receiver@test.com"},
    "origin": "Delhi", "destination": "Mumbai",
    "weight": 2.5, "deliveryCharge": 250.0,
    "status": "Booked", "description": "Test Package",
    "bookedAt": datetime.now(timezone.utc),
    "estimatedDelivery": datetime.now(timezone.utc),
}
result = db.parcels.insert_one(new_parcel)
print(f"  [OK] Parcel inserted! _id = {result.inserted_id}")
print(f"       trackingId = CPT-TEST-001 | status = Booked")

# ── TEST 2: READ ──────────────────────────────────────────────
print("\nTEST 2: READ — Fetch the inserted parcel")
print("-" * 40)
doc = db.parcels.find_one({"trackingId": "CPT-TEST-001"}, {"_id": 0})
print(f"  [OK] Found: {doc['trackingId']} | "
      f"{doc['origin']} to {doc['destination']} | "
      f"Weight: {doc['weight']}kg | Status: {doc['status']}")

# ── TEST 3: UPDATE ────────────────────────────────────────────
print("\nTEST 3: UPDATE — Change status from Booked to In Transit")
print("-" * 40)
before = db.parcels.find_one({"trackingId": "CPT-TEST-001"}, {"status": 1, "_id": 0})
db.parcels.update_one(
    {"trackingId": "CPT-TEST-001"},
    {"$set": {"status": "In Transit"}}
)
after = db.parcels.find_one({"trackingId": "CPT-TEST-001"}, {"status": 1, "_id": 0})
print(f"  [OK] Status updated: '{before['status']}' => '{after['status']}'")

# ── TEST 4: DELETE ────────────────────────────────────────────
print("\nTEST 4: DELETE — Remove the test parcel")
print("-" * 40)
del_result = db.parcels.delete_one({"trackingId": "CPT-TEST-001"})
verify = db.parcels.find_one({"trackingId": "CPT-TEST-001"})
print(f"  [OK] Deleted {del_result.deleted_count} document(s)")
print(f"       Verify: {'Not found - confirmed deleted' if verify is None else 'Still exists!'}")

# ── TEST 5: DUPLICATE ID ──────────────────────────────────────
print("\nTEST 5: DUPLICATE trackingId — Insert same ID twice")
print("-" * 40)
db.parcels.delete_one({"trackingId": "CPT-DUPE-001"})
base = {
    "trackingId": "CPT-DUPE-001",
    "sender":   {"name": "A", "phone": "+910000000001", "address": "X"},
    "receiver": {"name": "B", "phone": "+910000000002", "address": "Y"},
    "origin": "Delhi", "destination": "Mumbai",
    "weight": 1.0, "deliveryCharge": 100.0,
    "status": "Booked", "bookedAt": datetime.now(timezone.utc),
}
db.parcels.insert_one(base)
try:
    base.pop("_id", None)
    db.parcels.insert_one(base)
    print("  [FAIL] Duplicate was allowed!")
except DuplicateKeyError:
    print("  [OK] DuplicateKeyError raised correctly!")
    print("       MongoDB rejected duplicate trackingId = CPT-DUPE-001")
db.parcels.delete_one({"trackingId": "CPT-DUPE-001"})

# ── TEST 6: INVALID STATUS ────────────────────────────────────
print("\nTEST 6: INVALID DOCUMENT — Status not in allowed enum")
print("-" * 40)
try:
    db.parcels.insert_one({
        "trackingId": "CPT-INVALID-001",
        "sender":   {"name": "Bad", "phone": "+910000000003", "address": "X"},
        "receiver": {"name": "Bad", "phone": "+910000000004", "address": "Y"},
        "origin": "Delhi", "destination": "Mumbai",
        "weight": 1.0, "deliveryCharge": 100.0,
        "status": "FLYING",
        "bookedAt": datetime.now(timezone.utc),
    })
    print("  [FAIL] Invalid status was accepted!")
except WriteError:
    print("  [OK] WriteError raised — schema rejected status='FLYING'")
    print("       Allowed: Booked, Picked Up, In Transit, Out for Delivery,")
    print("                Delivered, Failed Delivery, Returned")

# ── TEST 7: NEGATIVE WEIGHT ───────────────────────────────────
print("\nTEST 7: INVALID DOCUMENT — Negative weight value")
print("-" * 40)
try:
    db.parcels.insert_one({
        "trackingId": "CPT-INVALID-002",
        "sender":   {"name": "Bad", "phone": "+910000000005", "address": "X"},
        "receiver": {"name": "Bad", "phone": "+910000000006", "address": "Y"},
        "origin": "Delhi", "destination": "Mumbai",
        "weight": -5.0,
        "deliveryCharge": 100.0,
        "status": "Booked",
        "bookedAt": datetime.now(timezone.utc),
    })
    print("  [FAIL] Negative weight was accepted!")
except WriteError:
    print("  [OK] WriteError raised — schema rejected weight = -5.0")
    print("       Rule: weight must be >= 0.01")

# ── TEST 8: MISSING REQUIRED FIELD ───────────────────────────
print("\nTEST 8: INVALID DOCUMENT — Missing required field 'sender'")
print("-" * 40)
try:
    db.parcels.insert_one({
        "trackingId": "CPT-INVALID-003",
        "receiver": {"name": "Bad", "phone": "+910000000007", "address": "Y"},
        "origin": "Delhi", "destination": "Mumbai",
        "weight": 1.0, "deliveryCharge": 100.0,
        "status": "Booked",
        "bookedAt": datetime.now(timezone.utc),
    })
    print("  [FAIL] Missing field was accepted!")
except WriteError:
    print("  [OK] WriteError raised — schema rejected missing 'sender' field")
    print("       Required: trackingId, sender, receiver, origin,")
    print("                 destination, weight, deliveryCharge, status, bookedAt")

print()
print("=" * 60)
print("  ALL 8 TESTS COMPLETED")
print("=" * 60)
