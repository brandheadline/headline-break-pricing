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
st.caption("Floor-first PYT pricing with current + legacy MLB teams")

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
# TEAM DEFINITIONS
# =========================================================
CURRENT_MLB_TEAMS = {
    "Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox",
    "Chicago Cubs","Chicago White Sox","Cincinnati Reds","Cleveland Guardians",
    "Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals",
    "Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers",
    "Minnesota Twins","New York Mets","New York Yankees","Oakland Athletics",
    "Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres",
    "San Francisco Giants","Seattle Mariners","St. Louis Cardinals",
    "Tampa Bay Rays","Texas Rangers","Toronto Blue Jays","Washington Nationals"
}

LEGACY_MLB_TEAMS = {
    "Montreal Expos",
    "Brooklyn Dodgers",
    "California Angels",
    "Washington Senators"
}

# =========================================================
# UPLOAD BECKETT CHECKLIST
# =========================================================
st.subheader("Upload Beckett Checklist (Excel)")

file = st.file_uploader(
    "Upload checklist (.xlsx)",
    type=["xlsx"]
)

if not file:
    st.stop()

# =========================================================
# LOAD FULL CHECKLIST
# =========================================================
df = pd.read_excel(file, sheet_name="Full Checklist")
df.columns = [str(c).strip().lower() for c in df.columns]

# Beckett layout: [#, Player, Team, Notes]
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
# CLASSIFY TEAM TYPE
# =========================================================
def classify_team(team):
    if team in CURRENT_MLB_TEAMS:
        return "current"
    elif team in LEGACY_MLB_TEAMS:
        return "legacy"
    else:
        return "ignore"

df["team_type"] = df["team"].apply(classify_team)
df = df[df["team_type"] != "ignore"]

# =========================================================
# TAG HOBBY SIGNALS
# =========================================================
df["rookie"] = df["notes"].str.contains(r"\bRC\b", flags=re.I, regex=True)
df["league_leaders"] = df["notes"].str.contains("league leaders", flags=re.I, regex=True)
df["combo"] = df["notes"].str.contains("combo", flags=re.I, regex=True)
df["team_card"] = df["notes"].str.contains("team card", flags=re.I, regex=True)

# =========================================================
# CHASE SCORING (OPINIONATED, SIMPLE)
# =========================================================
def score_row(r):
    score = 1  # base presence
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
# SPLIT CURRENT VS LEGACY
# =========================================================
current_df = df[df["team_type"] == "current"]
legacy_df = df[df["team_type"] == "legacy"]

# =========================================================
# AGGREGATE CURRENT TEAMS (ALWAYS 30)
# =========================================================
current_scores = (
    current_df.groupby("team")["score"]
    .sum()
    .reindex(sorted(CURRENT_MLB_TEAMS), fill_value=0)
)

legacy_teams = sorted(legacy_df["team"].unique())

num_current = len(current_scores)
num_legacy = len(legacy_teams)
num_total = num_current + num_legacy

# =========================================================
# FLOOR-FIRST PRICING
# =========================================================
floor_total = num_total * floor_price
remaining_pool = total_break_price - floor_total

if remaining_pool <= 0:
    st.error("Floor price too high for total break price.")
    st.stop()

total_current_score = current_scores.sum()

# Allocate ONLY to current teams
current_weights = current_scores / total_current_score
current_prices = floor_price + (current_weights * remaining_pool)

# Legacy teams stay at floor
legacy_prices = pd.Series(
    [floor_price] * num_legacy,
    index=legacy_teams
)

# =========================================================
# COMBINE RESULTS
# =========================================================
pricing = pd.concat([current_prices, legacy_prices]).reset_index()
pricing.columns = ["team", "suggested_price"]

# Hobby rounding
pricing["suggested_price"] = pricing["suggested_price"].round(-1)

# Final rounding reconciliation (safe)
rounding_diff = total_break_price - pricing["suggested_price"].sum()
pricing.loc[pricing["suggested_price"].idxmax(), "suggested_price"] += rounding_diff

# =========================================================
# OUTPUT
# =========================================================
st.subheader("Suggested PYT Pricing (Current + Legacy Teams)")

st.dataframe(
    pricing.sort_values("suggested_price", ascending=False),
    use_container_width=True
)

st.success(
    "Pricing generated with floor-first logic.\n"
    "Current teams receive chase allocation.\n"
    "Legacy teams included without distorting pricing."
)
