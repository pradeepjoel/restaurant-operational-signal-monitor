from __future__ import annotations

from pathlib import Path

from src.config import get_settings
from src.db import connect, init_db
from src.extract_osm import fetch_restaurants
from src.transform import transform_overpass_elements, utc_now_iso
from src.load import load_rows
from src.quality_checks import check_db_basic, check_rows_basic


def run(project_root: Path | None = None) -> None:
    settings = get_settings(project_root=project_root)
    snapshot_ts = utc_now_iso()

    if project_root is None:
        project_root = Path(__file__).resolve().parents[1]

    conn = connect(settings.db_path)
    try:
        init_db(conn, schema_path=project_root / "sql" / "schema.sql")

        raw = fetch_restaurants(
            overpass_url=settings.overpass_url,
            bbox=settings.bbox,
            user_agent=settings.user_agent,
            timeout_seconds=settings.overpass_timeout_seconds,
        )

        # These transformed rows are the external operational signal derived from public OSM data.
        rows = transform_overpass_elements(raw.get("elements", []), snapshot_ts=snapshot_ts)

        pre_issues = check_rows_basic(rows)
        if pre_issues:
            print("Pre-load quality check issues:")
            for msg in pre_issues:
                print(f"- {msg}")
            # Still continue: many issues are "warnings" for beginners.

        inserted_snapshots, upserted_current = load_rows(conn, rows)

        post_issues = check_db_basic(conn)
        if post_issues:
            print("Post-load quality check issues:")
            for msg in post_issues:
                print(f"- {msg}")

        print("Pipeline complete.")
        print(f"- Snapshot timestamp: {snapshot_ts}")
        print(f"- Restaurants fetched: {len(rows)}")
        print(f"- Snapshot rows inserted (idempotent): {inserted_snapshots}")
        print(f"- Current rows upserted: {upserted_current}")
        print(f"- SQLite DB: {settings.db_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    run()

