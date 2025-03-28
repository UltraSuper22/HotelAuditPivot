import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Room Pivot Tool", layout="wide")
st.title("🏨 Room Count Pivot Generator")
st.write("Upload a full CSV export and select one or more events to generate a nightly room count pivot.")

uploaded_file = st.file_uploader("Upload your full CSV export", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)

        required_columns = ["regular_checkin", "regular_checkout", "realeventstartdate", "orders orderitems__quantity", "name"]
        if not all(col in df.columns for col in required_columns):
            st.error("❌ Uploaded file is missing one or more required columns. Please make sure the export includes all needed fields.")
        else:
            # Remove rows with blank or missing quantity values
            df = df[df["orders orderitems__quantity"].notna() & (df["orders orderitems__quantity"].astype(str).str.strip() != "")]

            # Parse date columns
            df["regular_checkin"] = pd.to_datetime(df["regular_checkin"], errors="coerce")
            df["regular_checkout"] = pd.to_datetime(df["regular_checkout"], errors="coerce")
            df["realeventstartdate"] = pd.to_datetime(df["realeventstartdate"], errors="coerce")

            # Replace blank hotel/room with placeholders
            df["events hotels - hotelid__name"] = df["events hotels - hotelid__name"].fillna("Unknown Hotel")
            df["events hotelrooms - requiresitem__name"] = df["events hotelrooms - requiresitem__name"].fillna("Unknown Room")

            # Drop any rows still missing required values
            df = df.dropna(subset=["regular_checkin", "regular_checkout"])
            df["orders orderitems__quantity"] = df["orders orderitems__quantity"].astype(int)

            # Dropdown to select events
            event_names = sorted(df["name"].dropna().unique())
            if not event_names:
                st.warning("⚠️ No events found in the 'name' column.")
            else:
                selected_events = st.multiselect("Select one or more events to pivot:", options=event_names)

                if selected_events:
                    df = df[df["name"].isin(selected_events)]

                    # Loop through unique event dates
                    for event_date in sorted(df["realeventstartdate"].dt.date.unique()):
                        df_event = df[df["realeventstartdate"].dt.date == event_date]
                        expanded_rows = []

                        for _, row in df_event.iterrows():
                            if pd.isna(row["regular_checkin"]) or pd.isna(row["regular_checkout"]):
                                continue

                            nights = pd.date_range(start=row["regular_checkin"], end=row["regular_checkout"] - pd.Timedelta(days=1))

                            hotel = row["events hotels - hotelid__name"]
                            room = row["events hotelrooms - requiresitem__name"]

                            for night in nights:
                                for _ in range(row["orders orderitems__quantity"]):
                                    expanded_rows.append({
                                        "Event": row["name"],
                                        "Hotel": hotel,
                                        "Room": room,
                                        "Stay Date": night.date()
                                    })

                        expanded_df = pd.DataFrame(expanded_rows)

                        if not expanded_df.empty:
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
                        else:
                            st.info(f"ℹ️ No data to pivot for {event_date}.")
    except Exception as e:
        st.error(f"💥 Something went wrong: {e}")

