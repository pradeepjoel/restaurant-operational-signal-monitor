from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable


def utc_now_iso() -> str:
    """UTC timestamp suitable for SQLite TEXT column."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def infer_status_from_tags(tags: dict[str, Any]) -> str:
    """
    OSM doesn't provide real-time open/closed for a business.
    For this beginner-friendly project we infer a coarse "status" from tags:

    - closed: explicitly marked abandoned/disused/closed (common patterns)
    - open: otherwise (amenity=restaurant rows are considered open)
    - unknown: if tags are missing
    """
    if not tags:
        return "unknown"

    # Common "no longer active" signals in OSM tagging.
    closed_signals = [
        "abandoned:amenity",
        "disused:amenity",
        "was:amenity",
        "razed:amenity",
        "demolished:amenity",
        "closed:amenity",
    ]
    if any(k in tags for k in closed_signals):
        return "closed"

    if tags.get("disused") in {"yes", "true", "1"}:
        return "closed"

    if tags.get("abandoned") in {"yes", "true", "1"}:
        return "closed"

    return "open"


def element_center_lat_lon(element: dict[str, Any]) -> tuple[float, float] | None:
    """Return (lat, lon) for node, or center for way/relation."""
    if element.get("type") == "node":
        if "lat" in element and "lon" in element:
            return float(element["lat"]), float(element["lon"])
        return None

    center = element.get("center")
    if isinstance(center, dict) and "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])

    return None


def transform_overpass_elements(elements: Iterable[dict[str, Any]], snapshot_ts: str) -> list[dict[str, Any]]:
    """
    Transform raw Overpass elements into rows ready to load into SQLite.
    """
    rows: list[dict[str, Any]] = []

    for el in elements:
        osm_type = el.get("type")
        osm_id = el.get("id")
        if osm_type not in {"node", "way", "relation"} or osm_id is None:
            continue

        lat_lon = element_center_lat_lon(el)
        if lat_lon is None:
            continue
        lat, lon = lat_lon

        tags = el.get("tags") or {}
        if not isinstance(tags, dict):
            tags = {}

        status = infer_status_from_tags(tags)
        rows.append(
            {
                "snapshot_ts": snapshot_ts,
                "osm_type": osm_type,
                "osm_id": int(osm_id),
                "name": tags.get("name"),
                "lat": lat,
                "lon": lon,
                "status": status,
                "cuisine": tags.get("cuisine"),
                "opening_hours": tags.get("opening_hours"),
                "raw_tags_json": json.dumps(tags, ensure_ascii=False, sort_keys=True),
            }
        )

    return rows

