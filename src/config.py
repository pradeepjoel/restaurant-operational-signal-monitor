from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    """
    Beginner-friendly config.

    - BBOX format: "south,west,north,east" (lat,lon,lat,lon)
    - Default BBOX is centered on central Paris, small-ish area for quick demos.
    """

    overpass_url: str
    bbox: str
    db_path: Path
    user_agent: str
    overpass_timeout_seconds: int


def get_settings(project_root: Path | None = None) -> Settings:
    if project_root is None:
        # src/config.py -> src/ -> project root
        project_root = Path(__file__).resolve().parents[1]

    overpass_url = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    bbox = os.getenv("BBOX", "48.852,2.337,48.866,2.360")  # Paris (demo)
    db_path = Path(os.getenv("DB_PATH", str(project_root / "data" / "restaurants.sqlite")))
    user_agent = os.getenv("USER_AGENT", "restaurant-status-scraper/1.0 (contact: you@example.com)")

    timeout = int(os.getenv("OVERPASS_TIMEOUT_SECONDS", "60"))

    return Settings(
        overpass_url=overpass_url,
        bbox=bbox,
        db_path=db_path,
        user_agent=user_agent,
        overpass_timeout_seconds=timeout,
    )

