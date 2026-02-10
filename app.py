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
st.caption("Checklist-driven pricing anchored to secondary market")

# =========================================================
# USER INPUTS (CLEAN + FINAL)
# =========================================================
st.subheader("Break Inputs")

col1, col2 = st.columns(2)

break_format = col1.selectbox(
    "Break Format",
    ["PYT (Pick Your Team)", "PYP (Pick Your Player)"]
)

purchase_cost = col2.number_input(
    "Your Purchase Cost ($)",
    value=864,
    step=50
)

col3, col4 = st.columns(2)

secondary_market = col3.number_input(
    "Secondary Market Reference (Dave & Adam’s)",
    value=1665,
    step=25
)

fanatics_fee_pct = col4.number_input(
    "Fanatics Fee (%)",
    value=10.0,
    step=0.5
)

st.divider()

# =========================================================
# MLB TEAMS (MODERN)
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
# UPLOAD BECKETT CHECKLIST
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
# CHECKLIST SIGNAL TAGGING
# =========================================================
df["rookie"] = df["notes"].str.contains(r"\bRC\b", flags=re.I, regex=True)
df["league_leaders"] = df["notes"].str.contains("league leaders", flags=re.I, regex=True)
df["combo"] = df["notes"].str.contains("combo", flags=re.I, regex=True)
df["team_card"] = df["notes"].str.contains("team card", flags=re.I, regex=True)

# =========================================================
# SCORING (UNCHANGED CORE LOGIC)
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

total_score = summary["score"].sum()
summary["weight"] = summary["score"] / total_score

# =========================================================
# CHECKLIST STRENGTH → BREAK PREMIUM
# =========================================================
avg_score = summary["score"].mean()

if avg_score >= summary["score"].quantile(0.75):
    checklist_strength = "Strong"
    break_premium = 500
elif avg_score >= summary["score"].quantile(0.35):
    checklist_strength = "Average"
    break_premium = 300
else:
    checklist_strength = "Weak"
    break_premium = 150

# =========================================================
# TARGET GMV (DERIVED, NOT INPUT)
# =========================================================
target_gmv = secondary_market + break_premium

# =========================================================
# PRICE DISTRIBUTION
# =========================================================
summary["suggested_price"] = summary["weight"] * target_gmv
summary["suggested_price"] = summary["suggested_price"].round(-1)

# =========================================================
# ECONOMICS
# =========================================================
gross_revenue = summary["suggested_price"].sum()
fanatics_fees = gross_revenue * (fanatics_fee_pct / 100)
net_profit = gross_revenue - fanatics_fees - purchase_cost
profit_pct = (net_profit / purchase_cost) * 100

if net_profit >= 800:
    profit_quality = "Strong"
elif net_profit >= 400:
    profit_quality = "Acceptable"
else:
    profit_quality = "Thin"

# =========================================================
# DISPLAY
# =========================================================
st.subheader("Pricing Output")

summary["suggested_price"] = summary["suggested_price"].apply(lambda x: f"${int(x):,}")

st.dataframe(
    summary.sort_values(
        "suggested_price",
        ascending=False,
        key=lambda col: col.str.replace("$", "", regex=False).astype(int)
    ),
    use_container_width=True
)

st.subheader("Break Summary")

colA, colB, colC, colD = st.columns(4)

colA.metric("Checklist Strength", checklist_strength)
colB.metric("Target GMV", f"${target_gmv:,.0f}")
colC.metric("Net Profit", f"${net_profit:,.0f}", f"{profit_pct:.1f}%")
colD.metric("Profit Quality", profit_quality)
