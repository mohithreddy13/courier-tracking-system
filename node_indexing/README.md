# Node.js Indexing Module — Courier Parcel Tracking System

## Purpose

This isolated module demonstrates the **Node.js MongoDB indexing requirement** of the college MongoDB project. It targets the **same `courier_tracking` database** used by the Python/Flask application, but uses the **official MongoDB Node.js driver** (not Mongoose) exclusively for index management.

> All CRUD operations, schema validation, aggregation and parcel status tracking remain in the Python/Flask application using **PyMongo**.

---

## Architecture Explanation

| Concern | Technology | Files |
|---|---|---|
| CRUD (insert, find, update, delete) | Python / PyMongo | `parcel_service.py` |
| $jsonSchema validation | Python / PyMongo | `validation.py` |
| Aggregation pipelines | Python / PyMongo | `aggregation.py` |
| Status tracking | Python / PyMongo | `parcel_service.py` |
| Indexing (PyMongo alternative) | Python / PyMongo | `indexing.py` |
| **Indexing (Node.js demo)** | **Node.js driver** | **`node_indexing/index.js`** |

Both implementations are idempotent — MongoDB won't duplicate an index that already exists with the same definition.

---

## Indexes Created

### `parcels` collection

| Index Name | Key | Unique | Purpose |
|---|---|---|---|
| `_id_` | `{ _id: 1 }` | Yes | MongoDB default |
| `idx_trackingId_unique` | `{ trackingId: 1 }` | **Yes** | Ensures no duplicate tracking IDs |
| `idx_status` | `{ status: 1 }` | No | Speeds up status-filter queries |
| `idx_destination` | `{ destination: 1 }` | No | Accelerates destination queries / aggregations |
| `idx_bookedAt_desc` | `{ bookedAt: -1 }` | No | Fast date-range booking trend reports |

### `tracking_history` collection

| Index Name | Key | Unique | Purpose |
|---|---|---|---|
| `_id_` | `{ _id: 1 }` | Yes | MongoDB default |
| `idx_trackingId_updatedAt_compound` | `{ trackingId: 1, updatedAt: 1 }` | No | Compound index for timeline lookups |

---

## Setup and Run

```bash
# From the project root directory
cd node_indexing
npm install
node index.js
```

Or run from the project root:

```bash
cd "c:\Users\vijju\OneDrive\Desktop\courier tracking system\node_indexing"
npm install
node index.js
```

---

## Expected Output

```
╔══════════════════════════════════════════════════╗
║  Courier Tracking — Node.js Indexing Module      ║
╚══════════════════════════════════════════════════╝

Connected to MongoDB at mongodb://localhost:27017
Database: courier_tracking

[1] Creating / verifying indexes via Node.js driver:

  ── parcels ─────────────────────────────────────
  ✓ createIndex() → "idx_trackingId_unique"
  ✓ createIndex() → "idx_status"
  ✓ createIndex() → "idx_destination"
  ✓ createIndex() → "idx_bookedAt_desc"

  ── tracking_history ─────────────────────────────────────
  ✓ createIndex() → "idx_trackingId_updatedAt_compound"

[2] Listing all indexes via Node.js listIndexes():
  ...

[3] Summary:
  parcels          → 5 indexes
  tracking_history → 2 indexes

[4] Verify in MongoDB Compass:
  Open Compass → courier_tracking → parcels → Indexes tab
```

---

## Verification in MongoDB Compass

1. Open **MongoDB Compass** and connect to `mongodb://localhost:27017`
2. Navigate to **courier_tracking** → **parcels** → **Indexes** tab
3. You should see all 5 indexes listed (including the default `_id_`)
4. Repeat for **tracking_history** — you should see 2 indexes

---

## Which implementation to submit?

- **If instructor requires Node.js for indexing:** Run this module and reference it in your submission. The Python application already creates the same indexes via `validation.py`, but this module provides the explicit Node.js `createIndex()` + `listIndexes()` demonstration.
- **If instructor requires all operations in PyMongo:** Use `python indexing.py` instead and skip this module. All indexes are also created by `validation.py` during app startup.

Document your choice clearly in your project report.
