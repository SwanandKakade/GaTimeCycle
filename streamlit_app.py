# gann_cycle_clusters.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Gann Time Cycle Analyzer", layout="wide")

st.title("🔱 Multi-Swing + Cluster Detector ")

st.markdown("""
Input up to 3 swings (price + date), choose Gann angles, and detect **cross-swing clusters** (±N days).
Scaling logic uses your custom rules so projected cycles stay within a practical horizon.
""")

# -----------------------
# USER INPUT — Swings
# -----------------------
st.header("1️⃣ Enter Swing High/Low Points (Price + Date)")
swings = []
col1, col2, col3 = st.columns(3)
with col1:
    with st.expander("Swing 1 (optional)"):
        p1 = st.number_input("Swing 1 Price", value=210.0, step=0.01, key="p1")
        d1 = st.date_input("Swing 1 Date", value=datetime(2025, 4, 7), key="d1")
        swings.append({"name": "Swing 1", "price": float(p1), "date": datetime.combine(d1, datetime.min.time())})
with col2:
    with st.expander("Swing 2 (optional)"):
        p2 = st.number_input("Swing 2 Price", value=235.0, step=0.01, key="p2")
        d2 = st.date_input("Swing 2 Date", value=datetime(2025, 5, 9), key="d2")
        swings.append({"name": "Swing 2", "price": float(p2), "date": datetime.combine(d2, datetime.min.time())})
with col3:
    with st.expander("Swing 3 (optional)"):
        p3 = st.number_input("Swing 3 Price", value=198.0, step=0.01, key="p3")
        d3 = st.date_input("Swing 3 Date", value=datetime(2025, 6, 15), key="d3")
        swings.append({"name": "Swing 3", "price": float(p3), "date": datetime.combine(d3, datetime.min.time())})

# -----------------------
# Gann Angles selection
# -----------------------
st.header("2️⃣ Select Gann Angles")
all_gann_angles = [
    15, 21, 28, 30,
    45, 49, 55, 60, 72,
    81,90,99, 120,144,180
]
colA, colB = st.columns([1,3])

with colA:
    select_all = st.checkbox("Select All Angles", value=False)

if select_all:
    selected_angles = st.multiselect(
        "Choose angles to analyze",
        options=all_gann_angles,
        default=all_gann_angles
    )
else:
    selected_angles = st.multiselect(
        "Choose angles to analyze",
        options=all_gann_angles,
        default=[15, 21,28, 30, 45, 55, 60]  # your default set
    )

if not selected_angles:
    st.warning("⚠ Please select at least one angle!")
    st.stop()

# -----------------------
# Cluster settings
# -----------------------
st.header("3️⃣ Cluster Settings")
cluster_window = st.number_input("Cluster Window (±days)", min_value=1, max_value=30, value=3)
max_table_rows = st.number_input("Max table rows to display", min_value=5, max_value=200, value=50)

# -----------------------
# Custom scaling logic (your rules)
# -----------------------
def scale_price(price: float):
    """
    Custom scaling rules (user-specified):
      - if price >= 100000 -> divisor = 3000
      - elif price >= 25000 -> divisor = 500
      - elif price >= 10000 -> divisor = 100
      - elif price >= 1000  -> divisor = 10
      - elif price >= 500   -> divisor = 2
      - else                -> divisor = 1
    Returns (scaled_price, divisor)
    """
    if price >= 100000:
        d = 3000
    elif price >= 25000:
        d = 500
    elif price >= 10000:
        d = 100
    elif price >= 1000:
        d = 10
    elif price >= 500:
        d = 2
    else:
        d = 1
    return price / d, d

# -----------------------
# Compute cycles
# -----------------------
rows = []
for s in swings:
    # allow user to leave swing price=0? we keep even 0 but skip if not positive
    price = s["price"]
    if price is None:
        continue
    scaled, divisor = scale_price(price)
    for ang in selected_angles:
        rad = np.deg2rad(ang)
        days = scaled * np.sin(rad)
        days_r = int(round(days))
        cycle_date = s["date"] + timedelta(days=days_r)
        rows.append({
            "Swing": s["name"],
            "Price": price,
            "Scaled Price": round(scaled, 6),
            "Divisor": int(divisor),
            "Angle°": float(ang),
            "Days": int(days_r),
            "Cycle Date": cycle_date
        })

if len(rows) == 0:
    st.info("No swing data entered yet.")
    st.stop()

df = pd.DataFrame(rows)
df = df.sort_values("Cycle Date").reset_index(drop=True)

# -----------------------
# Cross-swing cluster detection
# -----------------------
cluster_flags = []
for i in range(len(df)):
    d_i = df.loc[i, "Cycle Date"]
    count = 0
    for j in range(len(df)):
        d_j = df.loc[j, "Cycle Date"]
        if abs((d_i - d_j).days) <= cluster_window:
            count += 1
    cluster_flags.append(count >= 2)

df["Cluster"] = ["YES" if flag else "" for flag in cluster_flags]
df["Cluster Count"] = [sum(1 for k in range(len(df)) if abs((df.loc[i, "Cycle Date"] - df.loc[k, "Cycle Date"]).days) <= cluster_window) for i in df.index]  # number in cluster per row

# -----------------------
# Display results
# -----------------------
st.header("📅 Gann Time Cycle Table + Cross-Swing Cluster Detection")
col_left, col_right = st.columns([3, 1])

with col_left:
    st.dataframe(df[["Swing", "Days", "Cycle Date", "Cluster", "Cluster Count"]].head(int(max_table_rows)), use_container_width=True)

with col_right:
    st.markdown("**Legend**")
    st.markdown("- **Cluster**: rows that are within ±%d days of at least one other projected date." % cluster_window)
    st.markdown("- **Cluster Count**: how many projected dates (across swings/angles) fall within the window.")
    #st.markdown("**Scaling rules**")
    #st.markdown("`>=100k -> /3000 ; >=25k -> /500 ; >=10k -> /100 ; >=1k -> /10 ; >=500 -> /2 ; else /1`")

# -----------------------
# Show only clustered rows
# -----------------------
st.subheader("🔥 Clustered Dates (High-Probability Windows)")
cluster_df = df[df["Cluster"] == "YES"].copy()
if not cluster_df.empty:
    # Show grouped by cluster date window (nearest date) to make clearer
    cluster_df = cluster_df.sort_values("Cycle Date").reset_index(drop=True)
    st.table(cluster_df[["Swing", "Days", "Cycle Date", "Cluster Count"]])
else:
    st.info("No clusters detected with current swings / angles / window.")

# -----------------------
# Optional: export as CSV
# -----------------------
csv = df.to_csv(index=False)
st.download_button("⬇️ Download full cycles CSV", data=csv, file_name="gann_cycles.csv", mime="text/csv")

# -----------------------
# Small summary
# -----------------------
st.markdown("---")
st.markdown(f"Computed {len(df)} cycle projections from {len(swings)} swings and {len(selected_angles)} angles.")
if not cluster_df.empty:
    st.success(f"Detected {cluster_df['Cluster Count'].max()} overlapping projections in a cluster (max cluster size).")
else:
    st.info("No cross-swing clusters found with the given parameters.")
