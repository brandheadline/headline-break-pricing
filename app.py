import streamlit as st
import pandas as pd
import re

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(
    page_title="Break Pricing Engine",
    layout="centered"
)

st.title("Break Pricing Engine")
st.caption("Checklist-driven pricing with real break economics")

# =========================================================
# BREAK INPUTS
# =========================================================
st.subheader("Break Inputs")

col1, col2, col3 = st.columns(3)

break_format = col1.selectbox(
    "Break Format",
    ["PYT (Pick Your Team)", "PYP (Pick Your Player)"]
)

total_break_price = col2.number_input(
    "Target Total Break Price ($)",
    value=4500,
    step=50
)

floor_price = col3.number_input(
    "Floor Spot Price ($)",
    value=35,
    step=5
)

st.divider()

# =========================================================
# COST & FEES
# =========================================================
st.subheader("Cost & Fees")

col4, col5, col6 = st.columns(3)

purchase_cost = col4.number_input(
    "Your Purchase Cost ($)",
    value=3200,
    step=50
)

market_cost = col5.number_input(
    "Secondary Market Reference ($)",
    value=3500,
    step=50
)

fanatics_fee_pct = col6.number_input(
    "Fanatics Fee (%)",
    value=10.0,
    step=0.5
)

st.divider()

# =========================================================
# TEAM DEFINITIONS
# =========================================================
MLB_TEAMS = sorted([
    "Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox",
    "Chicago Cubs","Chicago White Sox","Cincinnati Reds","Cleveland Guardians",
    "Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals",
    "Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers",
    "Minnesota Twins","New York Mets","New York Yankees","Oakland Athletics",
    "Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres",
    "San Francisco Giants","Seattle Mariners","St. Louis Cardinals",
    "Tampa Bay Rays","Texas Rangers","Toronto Blue Jays","Washington Nationals"
])

TEAM_MERGE_MAP = {
    "Montreal Expos": "Washington Nationals",
    "Washington Senators": "Washington Nationals",
    "Brooklyn Dodgers": "Los Angeles Dodgers",
    "New York Giants": "San Francisco Giants",
    "California Angels": "Los Angeles Angels",
    "Anaheim Angels": "Los Angeles Angels",
}

# =========================================================
# UPLOAD CHECKLIST
# =========================================================
st.subheader("Upload Beckett Checklist")

file = st.file_uploader("Upload checklist (.xlsx)", type=["xlsx"])
if not file:
    st.stop()

df = pd.read_excel(file, sheet_name="Full Checklist")
df.columns = [str(c).strip().lower() for c in df.columns]

df = df.iloc[:, 1:4]
df.columns = ["player", "team", "notes"]

df["player"] = df["player"].astype(str).str.strip()
df["team"] = df["team"].astype(str).str.strip()
df["notes"] = df["notes"].astype(str).str.strip()

df = df[
    (df["player"] != "") &
    (~df["player"].str.contains("nan", case=False)) &
    (df["team"] != "") &
    (~df["team"].str.contains("nan", case=False))
]

df["team"] = df["team"].replace(TEAM_MERGE_MAP)
df = df[df["team"].isin(MLB_TEAMS)]

# =========================================================
# TAG SIGNALS
# =========================================================
df["rookie"] = df["notes"].str.contains(r"\bRC\b", flags=re.I, regex=True)
df["league_leaders"] = df["notes"].str.contains("league leaders", flags=re.I, regex=True)
df["combo"] = df["notes"].str.contains("combo", flags=re.I, regex=True)
df["team_card"] = df["notes"].str.contains("team card", flags=re.I, regex=True)

# =========================================================
# SCORING
# =========================================================
def score_row(r):
    score = 1
    if r["rookie"]: score += 3
    if r["league_leaders"]: score += 2
    if r["combo"]: score += 2
    if r["team_card"]: score += 1
    return score

df["score"] = df.apply(score_row, axis=1)

# =========================================================
# GROUPING (PYT vs PYP)
# =========================================================
group_col = "team" if "PYT" in break_format else "player"

summary = (
    df.groupby(group_col)
      .agg(
          score=("score", "sum"),
          count=("score", "count")
      )
      .reset_index()
)

# =========================================================
# PRICING LOGIC
# =========================================================
num_spots = len(summary)
floor_total = num_spots * floor_price
remaining_pool = total_break_price - floor_total

if remaining_pool <= 0:
    st.error("Floor price too high for total break price.")
    st.stop()

summary["weight"] = summary["score"] / summary["score"].sum()
summary["suggested_price"] = floor_price + (summary["weight"] * remaining_pool)
summary["suggested_price"] = summary["suggested_price"].round(-1)

# =========================================================
# ECONOMICS
# =========================================================
gross_revenue = summary["suggested_price"].sum()
fanatics_fees = gross_revenue * (fanatics_fee_pct / 100)
net_revenue = gross_revenue - fanatics_fees
profit = net_revenue - purchase_cost
profit_pct = (profit / purchase_cost) * 100

# =========================================================
# OUTPUT
# =========================================================
st.subheader("Suggested Pricing")

summary["suggested_price"] = summary["suggested_price"].apply(lambda x: f"${int(x):,}")

st.dataframe(
    summary.sort_values("suggested_price", ascending=False),
    use_container_width=True
)

st.subheader("Break Economics")

eco_col1, eco_col2, eco_col3 = st.columns(3)

eco_col1.metric("Gross Revenue", f"${gross_revenue:,.0f}")
eco_col2.metric("Net Revenue (After Fees)", f"${net_revenue:,.0f}")
eco_col3.metric("Profit", f"${profit:,.0f}", f"{profit_pct:.1f}%")
