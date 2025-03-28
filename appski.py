import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Room Pivot Tool", layout="wide")
st.title("🏨 Room Count Pivot Generator")
st.write("Upload a full CSV export and select one or more events to generate a nightly room count pivot.")

uploaded_file = st.file_uploader("Upload your full CSV export", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Parse date columns
    df["regular_checkin"] = pd.to_datetime(df["regular_checkin"], errors="coerce")
    df["regular_checkout"] = pd.to_datetime(df["regular_checkout"], errors="coerce")
    df["realeventstartdate"] = pd.to_datetime(df["realeventstartdate"], errors="coerce")
    df = df.dropna(subset=["regular_checkin", "regular_checkout", "orders orderitems__quantity"])
    df["orders orderitems__quantity"] = df["orders orderitems__quantity"].astype(int)

    # Dropdown to select events
    event_names = sorted(df["name"].dropna().unique())
    selected_events = st.multiselect("Select one or more events to pivot:", options=event_names)

    if selected_events:
        df = df[df["name"].isin(selected_events)]

        # Loop through unique event dates
        all_pivot_frames = []
        for event_date in sorted(df["realeventstartdate"].dt.date.unique()):
            df_event = df[df["realeventstartdate"].dt.date == event_date]
            expanded_rows = []

            for _, row in df_event.iterrows():
                nights = pd.date_range(start=row["regular_checkin"], end=row["regular_checkout"] - pd.Timedelta(days=1))
                for night in nights:
                    for _ in range(row["orders orderitems__quantity"]):
                        expanded_rows.append({
                            "Event": row["name"],
                            "Hotel": row["events hotels - hotelid__name"],
                            "Room": row["events hotelrooms - requiresitem__name"],
                            "Stay Date": night.date()
                        })

            expanded_df = pd.DataFrame(expanded_rows)

            # Create pivot
            pivot_df = expanded_df.pivot_table(
                index=["Event", "Hotel", "Room"],
                columns="Stay Date",
                aggfunc="size",
                fill_value=0
            ).reset_index()

            st.subheader(f"Pivot for {event_date}")
            st.dataframe(pivot_df, use_container_width=True)

            # Allow download
            csv = pivot_df.to_csv(index=False)
            st.download_button(
                label=f"📥 Download CSV for {event_date}",
                data=csv,
                file_name=f"pivot_{event_date}.csv",
                mime="text/csv"
            )
