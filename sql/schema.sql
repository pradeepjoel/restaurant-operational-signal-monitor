-- SQLite schema for restaurant status snapshots + latest state.

PRAGMA foreign_keys = ON;

-- Historical snapshots (append-only). Idempotent by (snapshot_ts, osm_type, osm_id).
CREATE TABLE IF NOT EXISTS restaurant_snapshot (
  snapshot_ts TEXT NOT NULL,                 -- ISO-8601 UTC timestamp
  osm_type    TEXT NOT NULL,                 -- "node" | "way" | "relation"
  osm_id      INTEGER NOT NULL,
  name        TEXT,
  lat         REAL NOT NULL,
  lon         REAL NOT NULL,
  status      TEXT NOT NULL,                 -- "open" | "closed" | "unknown"
  cuisine     TEXT,
  opening_hours TEXT,
  raw_tags_json TEXT,                        -- JSON string for debugging/auditing
  PRIMARY KEY (snapshot_ts, osm_type, osm_id)
);

-- Latest "current" state. One row per OSM element.
CREATE TABLE IF NOT EXISTS restaurant_current (
  osm_type    TEXT NOT NULL,
  osm_id      INTEGER NOT NULL,
  name        TEXT,
  lat         REAL NOT NULL,
  lon         REAL NOT NULL,
  status      TEXT NOT NULL,
  cuisine     TEXT,
  opening_hours TEXT,
  last_seen_ts TEXT NOT NULL,                -- snapshot_ts that last updated this row
  raw_tags_json TEXT,
  PRIMARY KEY (osm_type, osm_id)
);

CREATE INDEX IF NOT EXISTS idx_snapshot_ts ON restaurant_snapshot(snapshot_ts);
CREATE INDEX IF NOT EXISTS idx_current_status ON restaurant_current(status);
