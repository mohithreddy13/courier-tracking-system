"""
aggregation.py — MongoDB aggregation pipelines via PyMongo.
All pipelines use collection.aggregate() with $match, $group,
$sort, $project and $count stages as required.
"""
from datetime import datetime, timezone, timedelta
from database import get_db


def _parcels():
    return get_db()["parcels"]


def _history():
    return get_db()["tracking_history"]


# ──────────────────────────────────────────────────────────
#  1. Parcel counts by status
# ──────────────────────────────────────────────────────────
def count_by_status() -> list[dict]:
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$project": {"status": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"count": -1}},
    ]
    return list(_parcels().aggregate(pipeline))


# ──────────────────────────────────────────────────────────
#  2. Delivered vs Pending summary
# ──────────────────────────────────────────────────────────
def delivered_vs_pending() -> dict:
    pipeline = [
        {
            "$group": {
                "_id": None,
                "delivered":  {"$sum": {"$cond": [{"$eq": ["$status", "Delivered"]}, 1, 0]}},
                "in_transit": {"$sum": {"$cond": [{"$eq": ["$status", "In Transit"]}, 1, 0]}},
                "pending":    {"$sum": {"$cond": [{"$in":  ["$status",
                                ["Booked", "Picked Up", "Out for Delivery"]]}, 1, 0]}},
                "failed":     {"$sum": {"$cond": [{"$eq": ["$status", "Failed Delivery"]}, 1, 0]}},
                "returned":   {"$sum": {"$cond": [{"$eq": ["$status", "Returned"]}, 1, 0]}},
                "total":      {"$sum": 1},
            }
        },
        {"$project": {"_id": 0}},
    ]
    results = list(_parcels().aggregate(pipeline))
    return results[0] if results else {
        "delivered": 0, "in_transit": 0, "pending": 0,
        "failed": 0, "returned": 0, "total": 0,
    }


# ──────────────────────────────────────────────────────────
#  3. Total delivery charges
# ──────────────────────────────────────────────────────────
def total_delivery_charges() -> float:
    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$deliveryCharge"}}},
        {"$project": {"_id": 0, "total": 1}},
    ]
    result = list(_parcels().aggregate(pipeline))
    return result[0]["total"] if result else 0.0


# ──────────────────────────────────────────────────────────
#  4. Top destination cities
# ──────────────────────────────────────────────────────────
def top_destinations(limit: int = 10) -> list[dict]:
    pipeline = [
        {"$group": {"_id": "$destination", "count": {"$sum": 1}}},
        {"$project": {"city": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    return list(_parcels().aggregate(pipeline))


# ──────────────────────────────────────────────────────────
#  5. Daily booking trends (last 30 days)
# ──────────────────────────────────────────────────────────
def daily_booking_trends(days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"bookedAt": {"$gte": since}}},
        {
            "$group": {
                "_id": {
                    "year":  {"$year":  "$bookedAt"},
                    "month": {"$month": "$bookedAt"},
                    "day":   {"$dayOfMonth": "$bookedAt"},
                },
                "count": {"$sum": 1},
            }
        },
        {
            "$project": {
                "_id": 0,
                "date": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": {
                            "$dateFromParts": {
                                "year":  "$_id.year",
                                "month": "$_id.month",
                                "day":   "$_id.day",
                            }
                        },
                    }
                },
                "count": 1,
            }
        },
        {"$sort": {"date": 1}},
    ]
    return list(_parcels().aggregate(pipeline))


# ──────────────────────────────────────────────────────────
#  6. Monthly booking trends
# ──────────────────────────────────────────────────────────
def monthly_booking_trends() -> list[dict]:
    pipeline = [
        {
            "$group": {
                "_id": {
                    "year":  {"$year":  "$bookedAt"},
                    "month": {"$month": "$bookedAt"},
                },
                "count": {"$sum": 1},
                "revenue": {"$sum": "$deliveryCharge"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "month": {
                    "$concat": [
                        {"$toString": "$_id.year"}, "-",
                        {"$cond": [
                            {"$lt": ["$_id.month", 10]},
                            {"$concat": ["0", {"$toString": "$_id.month"}]},
                            {"$toString": "$_id.month"},
                        ]},
                    ]
                },
                "count": 1,
                "revenue": 1,
            }
        },
        {"$sort": {"month": 1}},
    ]
    return list(_parcels().aggregate(pipeline))


# ──────────────────────────────────────────────────────────
#  7. Parcel stats for a date range
# ──────────────────────────────────────────────────────────
def stats_for_range(start: datetime, end: datetime) -> dict:
    pipeline = [
        {"$match": {"bookedAt": {"$gte": start, "$lte": end}}},
        {
            "$group": {
                "_id": None,
                "total":   {"$sum": 1},
                "revenue": {"$sum": "$deliveryCharge"},
                "avg_weight": {"$avg": "$weight"},
                "delivered": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Delivered"]}, 1, 0]}
                },
                "failed": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Failed Delivery"]}, 1, 0]}
                },
            }
        },
        {"$project": {"_id": 0}},
    ]
    result = list(_parcels().aggregate(pipeline))
    return result[0] if result else {
        "total": 0, "revenue": 0, "avg_weight": 0, "delivered": 0, "failed": 0
    }


# ──────────────────────────────────────────────────────────
#  8. Full dashboard summary (combines multiple pipelines)
# ──────────────────────────────────────────────────────────
def dashboard_summary() -> dict:
    summary = delivered_vs_pending()
    summary["totalCharges"]    = total_delivery_charges()
    summary["byStatus"]        = count_by_status()
    summary["topDestinations"] = top_destinations(7)
    summary["dailyTrends"]     = daily_booking_trends(30)
    summary["monthlyTrends"]   = monthly_booking_trends()
    return summary
