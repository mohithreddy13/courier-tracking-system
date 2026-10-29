# Courier Parcel Tracking System

A complete, professional courier management web application built for a **college MongoDB project**. Demonstrates CRUD operations, schema validation with `$jsonSchema`, aggregation pipelines, parcel status tracking, and indexing using both **PyMongo** (primary) and the **Node.js MongoDB driver** (indexing demonstration).

---

## Architecture

| Layer | Technology |
|---|---|
| Frontend | HTML, Vanilla CSS, JavaScript, Chart.js, Lucide Icons |
| Backend | Python 3.11+ with Flask |
| Database | MongoDB Community Server |
| Python driver | PyMongo |
| Node.js indexing demo | Official `mongodb` Node.js package |

### Why two backends?

The project requirements explicitly list both "Use PyMongo" and "Node.js indexing". This application satisfies both:
- **PyMongo** handles all CRUD, schema validation, aggregation and status tracking.
- **Node.js** (`node_indexing/index.js`) provides a separate, isolated demonstration of `createIndex()` and `listIndexes()` using the Node.js driver — both on the same database.

---

## Project Structure

```
courier tracking system/
├── app.py                  # Flask application + all routes
├── database.py             # MongoDB connection (PyMongo)
├── validation.py           # $jsonSchema validators + collection setup
├── parcel_service.py       # CRUD operations using PyMongo
├── aggregation.py          # Aggregation pipelines using PyMongo
├── indexing.py             # PyMongo indexing (alternative to Node.js)
├── seed_data.py            # 80-record seed script using PyMongo
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── .env.example            # Template
├── templates/
│   ├── base.html           # Sidebar + topbar layout
│   ├── dashboard.html      # Live stats + charts
│   ├── register.html       # Parcel registration form
│   ├── manage.html         # Searchable parcel table
│   ├── track.html          # Tracking timeline
│   ├── update_status.html  # Status updater
│   ├── analytics.html      # Aggregation charts
│   ├── database_info.html  # Live indexes + schema info
│   ├── view_parcel.html    # Full parcel detail
│   └── edit_parcel.html    # Edit form
├── static/
│   ├── css/style.css       # Premium design system
│   └── js/main.js          # Sidebar, modals, animations
└── node_indexing/
    ├── index.js            # Node.js createIndex() + listIndexes()
    ├── package.json
    └── README.md
```

---

## Setup & Run (Windows / VS Code)

### Prerequisites

- Python 3.11+
- MongoDB Community Server running on port 27017
- Node.js 18+ (for the indexing demo)

### Step 1 — Create Python Virtual Environment

```powershell
cd "c:\Users\vijju\OneDrive\Desktop\courier tracking system"
python -m venv venv
.\venv\Scripts\activate
```

### Step 2 — Install Python Dependencies

```powershell
pip install -r requirements.txt
```

### Step 3 — Verify MongoDB is Running

```powershell
# MongoDB Community Server should already be running as a service.
# If not, start it manually:
net start MongoDB
```

### Step 4 — Initialise Collections and Schema Validators

```powershell
python validation.py
```

Expected output:
```
Setting up MongoDB collections and validators …
  [+] Created collection 'parcels' with $jsonSchema validator.
  [+] Created collection 'tracking_history' with $jsonSchema validator.
  [+] Indexes created / confirmed via PyMongo.
Setup complete.
```

### Step 5 — Insert Sample Data (80 parcels)

```powershell
python seed_data.py
```

Expected output:
```
Seed complete: 80 parcels, ~300 tracking events inserted.
```

### Step 6 — Start the Flask Application

```powershell
python app.py
```

Open **http://localhost:5000** in your browser.

### Step 7 — Run Node.js Indexing Demonstration

```powershell
cd node_indexing
npm install
node index.js
cd ..
```

### Step 8 — Verify in MongoDB Compass

1. Connect to `mongodb://localhost:27017`
2. Open **courier_tracking** database
3. Check **parcels** → Indexes tab (should show 5 indexes)
4. Check **tracking_history** → Indexes tab (should show 2 indexes)
5. Check **parcels** → Validation tab to see the `$jsonSchema` validator

---

## MongoDB Features Demonstrated

### ✅ CRUD Operations (PyMongo)

| Operation | Method | File |
|---|---|---|
| Create parcel | `insert_one()` | `parcel_service.py` |
| Read all parcels | `find()` | `parcel_service.py` |
| Read by tracking ID | `find_one()` | `parcel_service.py` |
| Update parcel details | `update_one()` | `parcel_service.py` |
| Update parcel status | `update_one()` | `parcel_service.py` |
| Delete parcel | `delete_one()` | `parcel_service.py` |

### ✅ Schema Validation (`$jsonSchema`)

Defined in `validation.py` and applied via `db.create_collection()` with `validator=` parameter.

- **parcels**: validates required fields, embedded sender/receiver objects, positive weight, non-negative charge, enum status values, BSON date types.
- **tracking_history**: validates trackingId, status enum, location and updatedAt date.

### ✅ Aggregation Pipeline (PyMongo)

All pipelines in `aggregation.py` use `collection.aggregate()`:

| Report | Stages Used |
|---|---|
| Parcels by status | `$group`, `$project`, `$sort` |
| Delivered vs pending | `$group`, `$project` |
| Total charges | `$group`, `$project` |
| Top destinations | `$group`, `$project`, `$sort`, `$limit` |
| Daily booking trends | `$match`, `$group`, `$project`, `$sort` |
| Monthly trends | `$group`, `$project`, `$sort` |
| Date-range stats | `$match`, `$group`, `$project` |

### ✅ Parcel Status Tracking

7 statuses with validated forward-only transitions:
```
Booked → Picked Up → In Transit → Out for Delivery → Delivered
                                                  ↘ Failed Delivery → Returned
```

Each status change:
1. Validates the transition (prevents invalid moves)
2. Updates `parcels.status` via `update_one()`
3. Inserts a new event into `tracking_history` via `insert_one()`
4. Records timestamp, location and remarks

### ✅ Indexing

#### PyMongo (`indexing.py` / `validation.py`)
- `create_index()` on trackingId (unique), status, destination, bookedAt
- Compound `create_index()` on (trackingId, updatedAt) in tracking_history
- `list_indexes()` for verification

#### Node.js (`node_indexing/index.js`)
- `createIndex()` for the same index set using the Node.js driver
- `listIndexes()` to list and verify all indexes
- Runs against the same MongoDB database

---

## Pages

| URL | Page |
|---|---|
| `/` | Dashboard — live stats and charts |
| `/register` | Register a new parcel |
| `/manage` | Searchable parcel table with CRUD actions |
| `/track` | Track parcel by tracking ID |
| `/update-status` | Update shipment status with transition validation |
| `/analytics` | Aggregation charts and reports |
| `/database-info` | Live index metadata and schema validators |
| `/parcel/<id>` | Full parcel detail view |
| `/parcel/<id>/edit` | Edit parcel |

---

## Academic Notes

This project satisfies all mandatory requirements:

1. **CRUD** — Full create, read, update, delete using PyMongo in `parcel_service.py`
2. **MongoDB Schema Validation** — `$jsonSchema` validators on both collections in `validation.py`
3. **Aggregation Pipeline** — 7 pipelines in `aggregation.py` connected to Chart.js
4. **Parcel Status Tracking** — Transition-validated status updates with history events
5. **Indexing (Node.js)** — Isolated `node_indexing/index.js` using the Node.js driver
6. **PyMongo** — All primary database operations use PyMongo
