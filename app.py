import streamlit as st
import pandas as pd
import re

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(
    page_title="Beckett PYT Pricing Engine",
    layout="centered"
)

st.title("Beckett PYT Pricing Engine")
st.caption("SlabStox-style PYT pricing using Beckett checklist data")

# =========================================================
# INPUTS
# =========================================================
st.subheader("Break Inputs")

col1, col2 = st.columns(2)

total_break_price = col1.number_input(
    "Target Total Break Price ($)",
    value=4500,
    step=50
)

floor_price = col2.number_input(
    "Floor Team Price ($)",
    value=35,
    step=5
)

st.divider()

# =========================================================
# CANONICAL MLB TEAMS (MODERN)
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

# =========================================================
# LEGACY → MODERN TEAM MERGE MAP
# =========================================================
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

# =========================================================
# LOAD FULL CHECKLIST
# =========================================================
df = pd.read_excel(file, sheet_name="Full Checklist")
df.columns = [str(c).strip().lower() for c in df.columns]

# Expected Beckett layout
df = df.iloc[:, 1:4]
df.columns = ["player", "team", "notes"]

df["player"] = df["player"].astype(str).str.strip()
df["team"] = df["team"].astype(str).str.strip()
df["notes"] = df["notes"].astype(str).str.strip()

# Remove junk rows
df = df[
    (df["player"] != "") &
    (~df["player"].str.contains("nan", case=False)) &
    (df["team"] != "") &
    (~df["team"].str.contains("nan", case=False))
]

# =========================================================
# MERGE LEGACY TEAMS INTO MODERN TEAMS
# =========================================================
df["team"] = df["team"].replace(TEAM_MERGE_MAP)
df = df[df["team"].isin(MLB_TEAMS)]

# =========================================================
# TAG CHECKLIST SIGNALS
# =========================================================
df["rookie"] = df["notes"].str.contains(r"\bRC\b", flags=re.I, regex=True)
df["league_leaders"] = df["notes"].str.contains("league leaders", flags=re.I, regex=True)
df["combo"] = df["notes"].str.contains("combo", flags=re.I, regex=True)
df["team_card"] = df["notes"].str.contains("team card", flags=re.I, regex=True)

# =========================================================
# SCORE CHECKLIST STRENGTH
# =========================================================
def score_row(r):
    score = 1
    if r["rookie"]:
        score += 3
    if r["league_leaders"]:
        score += 2
    if r["combo"]:
        score += 2
    if r["team_card"]:
        score += 1
    return score

df["score"] = df.apply(score_row, axis=1)

# =========================================================
# AGGREGATE BY TEAM (30 TEAMS)
# =========================================================
team_summary = (
    df.groupby("team")
      .agg(
          team_score=("score", "sum"),
          card_count=("player", "count")
      )
      .reindex(MLB_TEAMS, fill_value=0)
      .reset_index()
)

total_score = team_summary["team_score"].sum()
total_cards = team_summary["card_count"].sum()

team_summary["checklist_pct"] = team_summary["card_count"] / total_cards

# =========================================================
# TEAM STRENGTH LABELS (SLABSTOX-STYLE)
# =========================================================
def strength_label(score):
    if score >= team_summary["team_score"].quantile(0.75):
        return "Strong"
    elif score >= team_summary["team_score"].quantile(0.35):
        return "Average"
    else:
        return "Weak"

team_summary["team_strength"] = team_summary["team_score"].apply(strength_label)

# =========================================================
# FLOOR-FIRST PRICING
# =========================================================
floor_total = len(MLB_TEAMS) * floor_price
remaining_pool = total_break_price - floor_total

if remaining_pool <= 0:
    st.error("Floor price too high for total break price.")
    st.stop()

team_summary["weight_pct"] = team_summary["team_score"] / total_score
team_summary["suggested_price"] = (
    floor_price + (team_summary["weight_pct"] * remaining_pool)
)

# Round to hobby-friendly pricing
team_summary["suggested_price"] = team_summary["suggested_price"].round(-1)

# Final rounding reconciliation
rounding_diff = total_break_price - team_summary["suggested_price"].sum()
team_summary.loc[team_summary["suggested_price"].idxmax(), "suggested_price"] += rounding_diff

# =========================================================
# FORMAT OUTPUT
# =========================================================
team_summary["suggested_price"] = team_summary["suggested_price"].apply(lambda x: f"${int(x):,}")
team_summary["checklist_pct"] = (team_summary["checklist_pct"] * 100).round(1).astype(str) + "%"

# =========================================================
# DISPLAY
# =========================================================
st.subheader("Suggested PYT Pricing (Merged Teams)")

display_cols = [
    "team",
    "team_strength",
    "checklist_pct",
    "suggested_price"
]

st.dataframe(
    team_summary[display_cols].sort_values(
        by="suggested_price",
        ascending=False,
        key=lambda col: col.str.replace("$", "", regex=False).astype(int)
    ),
    use_container_width=True
)

st.success(
    "Pricing generated using merged legacy teams, checklist strength, "
    "and SlabStox-style presentation."
)
