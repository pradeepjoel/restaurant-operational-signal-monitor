from __future__ import annotations

import sqlite3
from typing import Any, Iterable


SNAPSHOT_INSERT_SQL = """
INSERT OR IGNORE INTO restaurant_snapshot (
  snapshot_ts, osm_type, osm_id, name, lat, lon, status, cuisine, opening_hours, raw_tags_json
) VALUES (
  :snapshot_ts, :osm_type, :osm_id, :name, :lat, :lon, :status, :cuisine, :opening_hours, :raw_tags_json
);
"""


CURRENT_UPSERT_SQL = """
INSERT INTO restaurant_current (
  osm_type, osm_id, name, lat, lon, status, cuisine, opening_hours, last_seen_ts, raw_tags_json
) VALUES (
  :osm_type, :osm_id, :name, :lat, :lon, :status, :cuisine, :opening_hours, :snapshot_ts, :raw_tags_json
)
ON CONFLICT(osm_type, osm_id) DO UPDATE SET
  name = excluded.name,
  lat = excluded.lat,
  lon = excluded.lon,
  status = excluded.status,
  cuisine = excluded.cuisine,
  opening_hours = excluded.opening_hours,
  last_seen_ts = excluded.last_seen_ts,
  raw_tags_json = excluded.raw_tags_json;
"""


def load_rows(conn: sqlite3.Connection, rows: Iterable[dict[str, Any]]) -> tuple[int, int]:
    """
    Load rows into:
    - restaurant_snapshot (idempotent insert)
    - restaurant_current (upsert latest state)

    Returns (inserted_snapshots, upserted_current).
    """
    rows_list = list(rows)
    if not rows_list:
        return 0, 0

    cur = conn.cursor()

    # Snapshot table: append-only historical record of the operational signal at each run time.
    # Idempotent loading: INSERT OR IGNORE avoids duplicate inserts for same snapshot_ts + OSM key.
    cur.executemany(SNAPSHOT_INSERT_SQL, rows_list)
    inserted_snapshots = cur.rowcount if cur.rowcount != -1 else 0

    # Current state table: one latest row per restaurant OSM key (used by dashboard and decisions).
    # Upsert keeps this table fresh while preserving stable primary keys.
    cur.executemany(CURRENT_UPSERT_SQL, rows_list)
    upserted_current = len(rows_list)

    conn.commit()
    return inserted_snapshots, upserted_current

