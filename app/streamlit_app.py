from __future__ import annotations

from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from src.config import get_settings
from src.db import connect, init_db


def load_current_df(db_path: Path, project_root: Path) -> pd.DataFrame:
    conn = connect(db_path)
    try:
        init_db(conn, schema_path=project_root / "sql" / "schema.sql")
        df = pd.read_sql_query(
            """
            SELECT osm_type, osm_id, name, lat, lon, status, cuisine, opening_hours, last_seen_ts
            FROM restaurant_current
            """,
            conn,
        )
        return df
    finally:
        conn.close()


def main() -> None:
    st.set_page_config(page_title="Restaurant Operational Signal Monitor", layout="wide")

    project_root = Path(__file__).resolve().parents[1]
    settings = get_settings(project_root=project_root)

    st.title("Restaurant Operational Signal Monitor")
    st.caption("Suivi des signaux opérationnels des restaurants pour la prévision de la demande")
    st.caption("OpenStreetMap (Overpass API) -> SQLite -> Streamlit dashboard")
    st.info(
        "This app turns public restaurant open/closed data into an external operational signal. "
        "This signal can help demand forecasting, staffing, inventory, and anomaly interpretation."
    )
    st.info("Ce tableau transforme des données publiques en signaux utiles pour la prise de décision.")

    df = load_current_df(settings.db_path, project_root=project_root)

    if df.empty:
        st.warning(
            "No data yet. Run the pipeline first:\n\n"
            "`python -m src.run_pipeline`\n\n"
            "Then refresh this page."
        )
        return

    # Core operational signal metrics for quick decision context.
    total = int(len(df))
    by_status = df["status"].value_counts().to_dict()
    closed_unknown_count = int(by_status.get("closed", 0) + by_status.get("unknown", 0))

    # Data quality metrics.
    missing_names = int((df["name"].fillna("").astype(str).str.strip() == "").sum())
    missing_coords = int(df["lat"].isna().sum() + df["lon"].isna().sum())
    missing_opening_hours = int((df["opening_hours"].fillna("").astype(str).str.strip() == "").sum())
    duplicate_ids = int(df.duplicated(subset=["osm_type", "osm_id"]).sum())
    missing_opening_ratio = (missing_opening_hours / total) if total else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Restaurants (current)", total)
    c2.metric("Open", int(by_status.get("open", 0)))
    c3.metric("Closed / Unknown", closed_unknown_count)

    st.subheader("Data quality metrics")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Missing names", missing_names)
    q2.metric("Missing coordinates", missing_coords)
    q3.metric("Missing opening hours", missing_opening_hours)
    q4.metric("Duplicate restaurant IDs", duplicate_ids)

    st.subheader("Decision Insight")
    insight_messages: list[str] = []
    if closed_unknown_count > 0:
        insight_messages.append(
            "Some restaurants are currently closed/unknown. This may impact demand forecasting assumptions."
        )
    if missing_opening_ratio >= 0.3:
        insight_messages.append(
            "Missing opening-hours coverage is high, so forecast reliability may be weaker for time-based decisions."
        )
    if duplicate_ids > 0:
        insight_messages.append(
            "Duplicate restaurant IDs detected in current data; review ingestion quality before relying on downstream decisions."
        )

    if insight_messages:
        for message in insight_messages:
            st.warning(message)
    else:
        st.success("Data quality is strong and operational signals look stable for forecasting support.")

    st.subheader("Forecasting Relevance")
    st.markdown(
        "- Restaurant status can be used as an external feature for demand forecasting.\n"
        "- Opening hours can help align demand expectations by time horizon.\n"
        "- Snapshot history supports auditability and historical analysis of signal changes."
    )

    left, right = st.columns([1, 2], gap="large")

    with left:
        st.subheader("Status distribution")
        dist = df["status"].value_counts().rename_axis("status").reset_index(name="count")
        st.bar_chart(dist.set_index("status")["count"])

        st.subheader("Sample rows")
        st.dataframe(
            df[["name", "status", "cuisine", "opening_hours", "last_seen_ts"]].fillna(""),
            use_container_width=True,
            height=380,
        )

    with right:
        st.subheader("Map")
        map_df = df[["lat", "lon", "status", "name"]].dropna()

        # Color by status (RGBA)
        color_map = {
            "open": [46, 204, 113, 160],     # green-ish
            "closed": [231, 76, 60, 160],    # red-ish
            "unknown": [149, 165, 166, 160], # gray-ish
        }
        map_df = map_df.assign(
            color=map_df["status"].map(lambda s: color_map.get(str(s), color_map["unknown"]))
        )

        lat_center = float(map_df["lat"].mean())
        lon_center = float(map_df["lon"].mean())

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius=35,
            pickable=True,
            auto_highlight=True,
        )

        tooltip = {"text": "{name}\nStatus: {status}"}
        view_state = pdk.ViewState(latitude=lat_center, longitude=lon_center, zoom=13)

        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))

    st.divider()
    st.caption(f"SQLite DB: {settings.db_path}")
    st.caption(f"BBOX: {settings.bbox} (override via env var `BBOX`)")


if __name__ == "__main__":
    main()

