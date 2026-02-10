import streamlit as st
import pandas as pd
import re
import numpy as np

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(page_title="Break Pricing Engine", layout="centered")
st.title("Break Pricing Engine")
st.caption("Checklist + Market + Anchors + Momentum + Velocity")

# =========================================================
# USER INPUTS
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
# MARKET POPULARITY (STRUCTURAL, STABLE)
# =========================================================
LARGE_MARKET_TEAMS = {
    "New York Yankees","New York Mets",
    "Los Angeles Dodgers","Los Angeles Angels",
    "Boston Red Sox","Chicago Cubs",
    "San Francisco Giants","Philadelphia Phillies"
}

SMALL_MARKET_TEAMS = {
    "Miami Marlins","Oakland Athletics",
    "Kansas City Royals","Pittsburgh Pirates",
    "Cleveland Guardians","Colorado Rockies",
    "Milwaukee Brewers","Tampa Bay Rays"
}

def market_multiplier(team):
    if team in LARGE_MARKET_TEAMS:
        return 1.05
    if team in SMALL_MARKET_TEAMS:
        return 0.95
    return 1.00

# =========================================================
# MLB TEAMS + LEGACY MERGE MAP
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

# Beckett layout: index | player | team | notes
df = df.iloc[:, 1:4]
df.columns = ["player", "team", "notes"]

df = df[
    (~df["player"].isna()) &
    (~df["team"].isna())
]

df["team"] = df["team"].replace(TEAM_MERGE_MAP)
df = df[df["team"].isin(MLB_TEAMS)]

# =========================================================
# CHECKLIST SIGNALS
# =========================================================
df["rookie"] = df["notes"].str.contains(r"\bRC\b", flags=re.I, regex=True)
df["league_leaders"] = df["notes"].str.contains("league leaders", flags=re.I, regex=True)
df["combo"] = df["notes"].str.contains("combo", flags=re.I, regex=True)
df["team_card"] = df["notes"].str.contains("team card", flags=re.I, regex=True)

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
          base_score=("score", "sum"),
          card_count=("score", "count")
      )
      .reset_index()
)

# =========================================================
# STATEFUL MOMENTUM + VELOCITY
# =========================================================
st.subheader("Momentum & Market Velocity")

momentum_map = {"Hot": 1.10, "Neutral": 1.00, "Cold": 0.90}
velocity_map = {"Fast": 1.05, "Normal": 1.00, "Slow": 0.95}

if "momentum_state" not in st.session_state:
    st.session_state.momentum_state = {
        row[group_col]: "Neutral" for _, row in summary.iterrows()
    }

if "velocity_state" not in st.session_state:
    st.session_state.velocity_state = {
        row[group_col]: "Normal" for _, row in summary.iterrows()
    }

for _, row in summary.iterrows():
    name = row[group_col]
    c1, c2, c3 = st.columns([3, 2, 2])
    c1.markdown(f"**{name}**")

    st.session_state.momentum_state[name] = c2.selectbox(
        "Momentum",
        ["Neutral", "Hot", "Cold"],
        index=["Neutral","Hot","Cold"].index(st.session_state.momentum_state[name]),
        key=f"mom_{name}"
    )

    st.session_state.velocity_state[name] = c3.selectbox(
        "Velocity",
        ["Normal", "Fast", "Slow"],
        index=["Normal","Fast","Slow"].index(st.session_state.velocity_state[name]),
        key=f"vel_{name}"
    )

summary["Momentum"] = summary[group_col].map(st.session_state.momentum_state)
summary["Velocity"] = summary[group_col].map(st.session_state.velocity_state)

summary["momentum_multiplier"] = summary["Momentum"].map(momentum_map)
summary["velocity_multiplier"] = summary["Velocity"].map(velocity_map)

summary["market_multiplier"] = summary[group_col].apply(
    lambda x: market_multiplier(x) if break_format.startswith("PYT") else 1.0
)

# =========================================================
# ADJUSTED SCORE
# =========================================================
summary["adjusted_score"] = (
    summary["base_score"] *
    summary["momentum_multiplier"] *
    summary["velocity_multiplier"] *
    summary["market_multiplier"]
)

# =========================================================
# BREAK PREMIUM (SECONDARY + BRAND)
# =========================================================
avg_score = summary["base_score"].mean()

if avg_score >= summary["base_score"].quantile(0.75):
    checklist_strength, break_premium = "Strong", 500
elif avg_score >= summary["base_score"].quantile(0.35):
    checklist_strength, break_premium = "Average", 300
else:
    checklist_strength, break_premium = "Weak", 150

target_gmv = secondary_market + break_premium

# =========================================================
# DYNAMIC ANCHORS + TIERS (PRODUCT-SPECIFIC)
# =========================================================
summary = summary.sort_values("adjusted_score", ascending=False).reset_index(drop=True)

summary["tier"] = "Weak"
summary.loc[0:2, "tier"] = "Anchor"
summary.loc[3:7, "tier"] = "Strong"
summary.loc[8:17, "tier"] = "Average"

# =========================================================
# PRICE BANDS — MOMENTUM INSIDE TIER
# =========================================================
bands = {
    "Anchor": (180, 260),
    "Strong": (120, 180),
    "Average": (70, 120),
    "Weak": (40, 80),
}

score_min = summary["adjusted_score"].min()
score_max = summary["adjusted_score"].max()

def band_position(row):
    lo, hi = bands[row["tier"]]
    if score_max == score_min:
        return (lo + hi) / 2
    pct = (row["adjusted_score"] - score_min) / (score_max - score_min)
    return lo + pct * (hi - lo)

summary["band_price"] = summary.apply(band_position, axis=1)

# =========================================================
# NORMALIZE TO TARGET GMV
# =========================================================
summary["weight"] = summary["band_price"] / summary["band_price"].sum()
summary["suggested_price"] = (summary["weight"] * target_gmv).round(-1)

# =========================================================
# ECONOMICS
# =========================================================
gross = summary["suggested_price"].sum()
fees = gross * fanatics_fee_pct / 100
profit = gross - fees - purchase_cost
profit_pct = (profit / purchase_cost) * 100

profit_quality = "Strong" if profit >= 800 else "Acceptable" if profit >= 400 else "Thin"

# =========================================================
# DISPLAY
# =========================================================
st.subheader("Pricing Output")

summary["suggested_price"] = summary["suggested_price"].apply(lambda x: f"${int(x):,}")

st.dataframe(
    summary[[group_col, "tier", "Momentum", "Velocity", "card_count", "suggested_price"]],
    use_container_width=True
)

st.subheader("Break Summary")

a, b, c, d = st.columns(4)
a.metric("Checklist Strength", checklist_strength)
b.metric("Target GMV", f"${target_gmv:,.0f}")
c.metric("Net Profit", f"${profit:,.0f}", f"{profit_pct:.1f}%")
d.metric("Profit Quality", profit_quality)
