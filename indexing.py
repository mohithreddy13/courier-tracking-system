"""
indexing.py — PyMongo indexing implementation.
Use this when the instructor requires ALL database operations (including
indexing) to use PyMongo exclusively.

For the Node.js indexing demonstration, see node_indexing/index.js.
"""
from pymongo import ASCENDING, DESCENDING
from database import get_db


def create_indexes():
    """
    Create all required indexes using PyMongo create_index().
    Safe to call multiple times — MongoDB is idempotent for existing indexes.
    """
    db          = get_db()
    parcels     = db["parcels"]
    history     = db["tracking_history"]

    # 1. Unique index on trackingId (parcels)
    parcels.create_index(
        "trackingId",
        unique=True,
        name="idx_trackingId_unique",
    )

    # 2. Index on status (parcels) — speeds up status-filter queries
    parcels.create_index("status", name="idx_status")

    # 3. Index on destination (parcels) — speeds up destination queries
    parcels.create_index("destination", name="idx_destination")

    # 4. Index on bookedAt (parcels) — speeds up date-range aggregations
    parcels.create_index("bookedAt", name="idx_bookedAt")

    # 5. Compound index on (trackingId, updatedAt) in tracking_history
    history.create_index(
        [("trackingId", ASCENDING), ("updatedAt", ASCENDING)],
        name="idx_trackingId_updatedAt_compound",
    )

    print("[PyMongo] All indexes created / confirmed.")


def list_indexes():
    """Return index metadata for both collections using list_indexes()."""
    db = get_db()
    result = {}
    for col_name in ["parcels", "tracking_history"]:
        col = db[col_name]
        result[col_name] = [
            {
                "name":   idx["name"],
                "key":    dict(idx["key"]),
                "unique": idx.get("unique", False),
            }
            for idx in col.list_indexes()
        ]
    return result


if __name__ == "__main__":
    create_indexes()
    import json
    print(json.dumps(list_indexes(), indent=2))
