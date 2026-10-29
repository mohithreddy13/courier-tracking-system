/**
 * node_indexing/index.js
 * ────────────────────────────────────────────────────────────
 * Node.js Indexing Demonstration for the Courier Parcel
 * Tracking System (MongoDB College Project).
 *
 * Uses the official MongoDB Node.js driver (NOT Mongoose).
 * Targets the same `courier_tracking` database as the Python
 * Flask application.
 *
 * Run with:  node node_indexing/index.js
 *   (from the project root)
 * ────────────────────────────────────────────────────────────
 */

require("dotenv").config({ path: "../.env" });
const { MongoClient } = require("mongodb");

const MONGO_URI = process.env.MONGO_URI || "mongodb://localhost:27017";
const DB_NAME   = process.env.DB_NAME   || "courier_tracking";

// ─────────────────────────────────────────────────────────────
//  Index definitions
// ─────────────────────────────────────────────────────────────
const PARCEL_INDEXES = [
  {
    key:     { trackingId: 1 },
    options: { unique: true, name: "idx_trackingId_unique" },
    purpose: "Ensures each parcel has a globally unique tracking ID. " +
             "Used by find_one() and as the primary lookup key.",
  },
  {
    key:     { status: 1 },
    options: { name: "idx_status" },
    purpose: "Speeds up status-filter queries (e.g. find all 'In Transit' parcels) " +
             "and the $match stage in status-distribution aggregations.",
  },
  {
    key:     { destination: 1 },
    options: { name: "idx_destination" },
    purpose: "Accelerates destination-filter queries and the top-destinations " +
             "$group aggregation pipeline.",
  },
  {
    key:     { bookedAt: -1 },
    options: { name: "idx_bookedAt_desc" },
    purpose: "Enables efficient sorting by booking date and fast date-range " +
             "queries used in daily/monthly booking trend reports.",
  },
];

const HISTORY_INDEXES = [
  {
    key:     { trackingId: 1, updatedAt: 1 },
    options: { name: "idx_trackingId_updatedAt_compound" },
    purpose: "Compound index used when fetching the chronological timeline " +
             "for a specific parcel (find + sort on both fields simultaneously).",
  },
];

// ─────────────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────────────
async function createIndexes(collection, definitions, colName) {
  console.log(`\n  ── ${colName} ─────────────────────────────────────`);
  for (const def of definitions) {
    try {
      const result = await collection.createIndex(def.key, def.options);
      console.log(`  ✓ createIndex() → "${result}"`);
      console.log(`    Key    : ${JSON.stringify(def.key)}`);
      console.log(`    Unique : ${def.options.unique || false}`);
      console.log(`    Purpose: ${def.purpose}`);
    } catch (err) {
      // Index already exists with the same definition — safe to ignore
      if (err.code === 85 || err.code === 86) {
        console.log(`  ~ Index "${def.options.name}" already exists — skipped.`);
      } else {
        console.error(`  ✗ Failed to create "${def.options.name}":`, err.message);
      }
    }
  }
}

async function listIndexes(collection, colName) {
  console.log(`\n  listIndexes() for ${colName}:`);
  const indexes = await collection.listIndexes().toArray();
  for (const idx of indexes) {
    console.log(`    • ${idx.name.padEnd(40)} key: ${JSON.stringify(idx.key)}${idx.unique ? "  [UNIQUE]" : ""}`);
  }
  return indexes;
}

// ─────────────────────────────────────────────────────────────
//  Main
// ─────────────────────────────────────────────────────────────
async function main() {
  const client = new MongoClient(MONGO_URI);

  try {
    await client.connect();
    console.log("╔══════════════════════════════════════════════════╗");
    console.log("║  Courier Tracking — Node.js Indexing Module      ║");
    console.log("╚══════════════════════════════════════════════════╝");
    console.log(`\nConnected to MongoDB at ${MONGO_URI}`);
    console.log(`Database: ${DB_NAME}`);

    const db      = client.db(DB_NAME);
    const parcels = db.collection("parcels");
    const history = db.collection("tracking_history");

    // ── Create indexes using Node.js driver ──
    console.log("\n[1] Creating / verifying indexes via Node.js driver:");
    await createIndexes(parcels, PARCEL_INDEXES, "parcels");
    await createIndexes(history, HISTORY_INDEXES, "tracking_history");

    // ── List all indexes using Node.js driver ──
    console.log("\n[2] Listing all indexes via Node.js listIndexes():");
    const parcelIdx  = await listIndexes(parcels, "parcels");
    const historyIdx = await listIndexes(history, "tracking_history");

    console.log("\n[3] Summary:");
    console.log(`  parcels          → ${parcelIdx.length} indexes`);
    console.log(`  tracking_history → ${historyIdx.length} indexes`);

    console.log("\n[4] Verify in MongoDB Compass:");
    console.log("  Open Compass → courier_tracking → parcels → Indexes tab");
    console.log("  You should see all 5 indexes (including _id_ default).\n");

    console.log("╔══════════════════════════════════════════════════╗");
    console.log("║  Node.js indexing demonstration complete.        ║");
    console.log("║  Main Python application uses PyMongo for all   ║");
    console.log("║  CRUD, validation, aggregation and tracking.    ║");
    console.log("╚══════════════════════════════════════════════════╝\n");

  } finally {
    await client.close();
  }
}

main().catch(err => {
  console.error("Fatal error:", err);
  process.exit(1);
});
