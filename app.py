import streamlit as st
import pandas as pd
import re
import numpy as np

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(page_title="Break Pricing Engine", layout="centered")

# --- Toggle color override (GREEN = ON) ---
st.markdown("""
<style>
div[data-testid="stToggle"] label {
    font-weight: 600;
}
div[data-testid="stToggle"] input:checked + div {
    background-color: #22c55e !important; /* green */
}
</style>
""", unsafe_allow_html=True)

st.title("Break Pricing Engine")
st.caption("Checklist + Market + Anchors + Momentum + Velocity")

# =========================================================
# USER INPUTS
# =========================================================
st.subheader("Break Inputs")

c1, c2 = st.columns(2)

break_format = c1.selectbox(
    "Break Format",
    ["PYT (Pick Your Team)", "PYP (Pick Your Player)"]
)

purchase_cost = c2.number_input(
    "Your Purchase Cost ($)",
    value=864,
    step=50
)

c3, c4 = st.columns(2)

secondary_market = c3.number_input(
    "Secondary Market Reference (Dave & Adam’s)",
    value=1665,
    step=25
)

fanatics_fee_pct = c4.number_input(
    "Fanatics Fee (%)",
    value=10.0,
    step=0.5
)

st.divider()

# =========================================================
# MARKET POPULARITY TOGGLE
# =========================================================
st.subheader("Market Popularity Adjustment")

apply_market_popularity = st.toggle(
    "Apply Market Popularity (recommended)",
    value=True,
    help="Applies long-term hobby liquidity bias for large vs small market teams"
)

# =========================================================
# MARKET POPULARITY DEFINITIONS
# =========================================================
LARGE_MARKET = {
    "New York Yankees","Los Angeles Dodgers","Boston Red Sox",
    "Chicago Cubs","New York Mets","San Francisco Giants",
    "Philadelphia Phillies","Los Angeles Angels"
}

SMALL_MARKET = {
    "Miami Marlins","Oakland Athletics","Kansas City Royals",
    "Pittsburgh Pirates","Cleveland Guardians",
    "Colorado Rockies","Milwaukee Brewers","Tampa Bay Rays"
}

def market_mult(team):
    if not apply_market_popularity:
        return 1.0
    if team in LARGE_MARKET:
        return 1.08
    if team in SMALL_MARKET:
        return 0.92
    return 1.00

# =========================================================
# TEAM MERGE MAP
# =========================================================
TEAM_MERGE = {
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
df.columns = [c.lower().strip() for c in df.columns]

df = df.iloc[:, 1:4]
df.columns = ["player", "team", "notes"]

df = df.dropna(subset=["player", "team"])
df["team"] = df["team"].replace(TEAM_MERGE)

# =========================================================
# CHECKLIST SIGNALS
# =========================================================
df["rookie"] = df["notes"].str.contains(r"\bRC\b", flags=re.I, regex=True)
df["league"] = df["notes"].str.contains("league leaders", flags=re.I, regex=True)
df["combo"] = df["notes"].str.contains("combo", flags=re.I, regex=True)

def score(r):
    s = 1
    if r["rookie"]: s += 3
    if r["league"]: s += 2
    if r["combo"]: s += 2
    return s

df["score"] = df.apply(score, axis=1)

# =========================================================
# GROUPING
# =========================================================
group_col = "team" if "PYT" in break_format else "player"

summary = (
    df.groupby(group_col)
      .agg(base_score=("score", "sum"), card_count=("score", "count"))
      .reset_index()
)

# =========================================================
# STATEFUL MOMENTUM & VELOCITY
# =========================================================
st.subheader("Momentum & Velocity")

mom_map = {"Hot": 1.20, "Neutral": 1.00, "Cold": 0.85}
vel_map = {"Fast": 1.15, "Normal": 1.00, "Slow": 0.85}

if "mom_state" not in st.session_state:
    st.session_state.mom_state = {row[group_col]: "Neutral" for _, row in summary.iterrows()}

if "vel_state" not in st.session_state:
    st.session_state.vel_state = {row[group_col]: "Normal" for _, row in summary.iterrows()}

for _, row in summary.iterrows():
    name = row[group_col]
    a, b, c = st.columns([3, 2, 2])
    a.markdown(f"**{name}**")

    st.session_state.mom_state[name] = b.selectbox(
        "Momentum", ["Neutral", "Hot", "Cold"],
        index=["Neutral","Hot","Cold"].index(st.session_state.mom_state[name]),
        key=f"mom_{name}"
    )

    st.session_state.vel_state[name] = c.selectbox(
        "Velocity", ["Normal", "Fast", "Slow"],
        index=["Normal","Fast","Slow"].index(st.session_state.vel_state[name]),
        key=f"vel_{name}"
    )

summary["momentum_mult"] = summary[group_col].map(lambda x: mom_map[st.session_state.mom_state[x]])
summary["velocity_mult"] = summary[group_col].map(lambda x: vel_map[st.session_state.vel_state[x]])
summary["market_mult"] = summary[group_col].map(
    lambda x: market_mult(x) if break_format.startswith("PYT") else 1.0
)

# =========================================================
# ADJUSTED WEIGHT (LIVE REBALANCING)
# =========================================================
summary["adjusted_weight"] = (
    summary["base_score"]
    * summary["momentum_mult"]
    * summary["velocity_mult"]
    * summary["market_mult"]
)

# =========================================================
# TARGET GMV
# =========================================================
avg = summary["base_score"].mean()
premium = 500 if avg >= summary["base_score"].quantile(0.75) else 300 if avg >= summary["base_score"].quantile(0.35) else 150
target_gmv = secondary_market + premium

# =========================================================
# PRICE DISTRIBUTION
# =========================================================
summary["weight"] = summary["adjusted_weight"] / summary["adjusted_weight"].sum()
summary["raw_price"] = summary["weight"] * target_gmv

summary["raw_price"] = summary["raw_price"].clip(lower=40)
summary["raw_price"] *= target_gmv / summary["raw_price"].sum()

summary["suggested_price"] = summary["raw_price"].round(-1).astype(int)

# =========================================================
# ECONOMICS
# =========================================================
gross = summary["suggested_price"].sum()
fees = gross * fanatics_fee_pct / 100
profit = gross - fees - purchase_cost

# =========================================================
# DISPLAY
# =========================================================
st.subheader("Pricing Output")

summary["Price"] = summary["suggested_price"].apply(lambda x: f"${x:,}")

st.dataframe(
    summary[[group_col, "card_count", "Price"]],
    use_container_width=True
)

st.subheader("Break Summary")

a, b, c = st.columns(3)
a.metric("Target GMV", f"${target_gmv:,.0f}")
b.metric("Net Profit", f"${profit:,.0f}")
c.metric("Fees", f"${fees:,.0f}")

# =========================================================
# EXPLANATION
# =========================================================
st.divider()
st.subheader("How These Prices Are Calculated")

st.markdown("""
**This pricing engine mirrors real-world PYT behavior.**

• Anchors to secondary market pricing  
• Applies a break premium based on checklist quality  
• Scores checklist depth (base, rookies, combos, league leaders)  
• Applies behavioral adjustments:
  – Market popularity (toggleable)
  – Momentum (news/hype)
  – Velocity (sell-through speed)

These adjustments **do not create value — they redistribute it**.

All prices are normalized to ensure total GMV remains accurate and profit is transparent.
""")
