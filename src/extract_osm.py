from __future__ import annotations

import json
from typing import Any

import requests


def build_overpass_query(bbox: str, timeout_seconds: int) -> str:
    """
    Query restaurants from a bounding box.

    We include:
    - nodes with amenity=restaurant
    - ways/relations with amenity=restaurant (center point returned by Overpass with "out center")
    """
    # bbox is "south,west,north,east"
    timeout_seconds = max(5, int(timeout_seconds))
    return f"""
    [out:json][timeout:{timeout_seconds}];
    (
      node["amenity"="restaurant"]({bbox});
      way["amenity"="restaurant"]({bbox});
      relation["amenity"="restaurant"]({bbox});
    );
    out tags center;
    """


def fetch_restaurants(overpass_url: str, bbox: str, user_agent: str, timeout_seconds: int = 60) -> dict[str, Any]:
    """
    Call the Overpass API and return the parsed JSON response.

    Uses POST (recommended for larger queries).
    """
    query = build_overpass_query(bbox, timeout_seconds=timeout_seconds)
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }

    resp = requests.post(
        overpass_url,
        data={"data": query},
        headers=headers,
        timeout=timeout_seconds,
    )
    resp.raise_for_status()

    data = resp.json()
    if "elements" not in data:
        raise ValueError(f"Unexpected Overpass response: {json.dumps(data)[:500]}")
    return data

