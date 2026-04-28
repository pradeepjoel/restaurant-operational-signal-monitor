from __future__ import annotations

import sqlite3
from typing import Any, Iterable


ALLOWED_STATUS = {"open", "closed", "unknown"}


def check_rows_basic(rows: Iterable[dict[str, Any]]) -> list[str]:
    """
    Basic checks on transformed rows before loading.

    Returns a list of human-readable issues (empty list means "looks good").
    """
    issues: list[str] = []
    seen_keys: set[tuple[str, int]] = set()

    rows_list = list(rows)
    if not rows_list:
        issues.append("No rows to load (Overpass returned 0 restaurants for your BBOX).")
        return issues

    for r in rows_list:
        osm_type = r.get("osm_type")
        osm_id = r.get("osm_id")
        lat = r.get("lat")
        lon = r.get("lon")
        status = r.get("status")

        if osm_type not in {"node", "way", "relation"}:
            issues.append(f"Invalid osm_type: {osm_type!r}")
        if not isinstance(osm_id, int):
            issues.append(f"Invalid osm_id: {osm_id!r}")

        try:
            lat_f = float(lat)
            lon_f = float(lon)
            if not (-90 <= lat_f <= 90):
                issues.append(f"Latitude out of range for {(osm_type, osm_id)}: {lat_f}")
            if not (-180 <= lon_f <= 180):
                issues.append(f"Longitude out of range for {(osm_type, osm_id)}: {lon_f}")
        except Exception:
            issues.append(f"Missing/invalid lat/lon for {(osm_type, osm_id)}: lat={lat!r} lon={lon!r}")

        if status not in ALLOWED_STATUS:
            issues.append(f"Invalid status for {(osm_type, osm_id)}: {status!r}")

        key = (str(osm_type), int(osm_id)) if isinstance(osm_id, int) else (str(osm_type), -1)
        if key in seen_keys:
            issues.append(f"Duplicate OSM element in batch: {key}")
        else:
            seen_keys.add(key)

    # Keep output small and beginner-friendly.
    return issues[:50]


def check_db_basic(conn: sqlite3.Connection) -> list[str]:
    """
    Basic checks after loading:
    - current table has rows
    - status distribution only contains allowed values
    """
    issues: list[str] = []

    row = conn.execute("SELECT COUNT(*) AS n FROM restaurant_current").fetchone()
    n = int(row["n"]) if row else 0
    if n == 0:
        issues.append("restaurant_current is empty after load.")

    bad = conn.execute(
        """
        SELECT status, COUNT(*) AS n
        FROM restaurant_current
        WHERE status NOT IN ('open','closed','unknown')
        GROUP BY status
        """
    ).fetchall()
    for r in bad:
        issues.append(f"Unexpected status in DB: {r['status']!r} count={r['n']}")

    return issues

