import streamlit as st
import pandas as pd
import numpy as np

# =================================================
# PAGE CONFIG
# =================================================
st.set_page_config(
    page_title="Headline Break Pricing Engine v3.1",
    layout="centered"
)

st.title("Headline Break Pricing Engine")
st.caption("Checklist-aware. Sport-aware. Rookie-driven. No guessing.")

# =================================================
# SPORT PROFILES
# =================================================
SPORT_PROFILES = {
    "Baseball (MLB)": {
        "rookie_keywords": ["rc", "rookie"],
        "auto_keywords": ["auto", "autograph"],
        "patch_keywords": ["patch", "relic", "memorabilia"],
        "insert_keywords": ["insert"],
        "variation_keywords": ["variation", "parallel"],
        "weights": {
            "base": 1.0,
            "rookie": 3.0,
            "auto": 6.0,
            "patch": 7.0,
            "insert": 2.0,
            "variation": 2.5
        }
    },
    "Football (NFL)": {
        "rookie_keywords": ["rc", "rookie"],
        "auto_keywords": ["auto", "autograph"],
        "patch_keywords": ["patch", "shield", "logo"],
        "insert_keywords": ["insert"],
        "variation_keywords": ["parallel"],
        "weights": {
            "base": 1.0,
            "rookie": 4.0,
            "auto": 7.0,
            "patch": 8.0,
            "insert": 2.5,
            "variation": 3.0
        }
    },
    "Basketball (NBA)": {
        "rookie_keywords": ["rc", "rookie"],
        "auto_keywords": ["auto"],
        "patch_keywords": ["patch", "tag", "logoman"],
        "insert_keywords": ["insert"],
        "variation_keywords": ["parallel"],
        "weights": {
            "base": 1.0,
            "rookie": 4.5,
            "auto": 7.5,
            "patch": 9.0,
            "insert": 3.0,
            "variation": 3.5
        }
    },
    "Soccer": {
        "rookie_keywords": ["rc", "rookie"],
        "auto_keywords": ["auto"],
        "patch_keywords": ["patch"],
        "insert_keywords": ["insert"],
        "variation_keywords": ["parallel"],
        "weights": {
            "base": 1.0,
            "rookie": 3.5,
            "auto": 6.5,
            "patch": 7.5,
            "insert": 2.5,
            "variation": 3.0
        }
    },
    "Non-Sport (Star Wars / Disney)": {
        "rookie_keywords": [],
        "auto_keywords": ["auto"],
        "patch_keywords": [],
        "insert_keywords": ["insert"],
        "variation_keywords": ["parallel"],
        "weights": {
            "base": 1.0,
            "auto": 8.0,
            "insert": 3.0,
            "variation": 3.5
        }
    }
}

# =================================================
# SPORT SELECTION
# =================================================
st.header("Product Context")
sport = st.selectbox("Select sport / category", list(SPORT_PROFILES.keys()))
profile = SPORT_PROFILES[sport]

# =================================================
# CHECKLIST INGESTION
# =================================================
st.header("Checklist Upload (Strongly Recommended)")
uploaded = st.file_uploader("Upload Beckett Checklist (Excel)", type=["xlsx"])

if not uploaded:
    st.info("Upload a checklist to continue.")
    st.stop()

xls = pd.ExcelFile(uploaded)
sheets = {s.lower(): s for s in xls.sheet_names}

if "teams" not in sheets:
    st.error("Checklist must contain a Teams sheet.")
    st.stop()

teams_df = xls.parse(sheets["teams"])
team_col = [c for c in teams_df.columns if "team" in c.lower()]
if not team_col:
    st.error("Teams sheet must contain a Team column.")
    st.stop()

team_col = team_col[0]

# =================================================
# CARD CLASSIFICATION
# =================================================
def score_row(row):
    text = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
    score = profile["weights"]["base"]

    for k in profile["rookie_keywords"]:
        if k in text:
            score += profile["weights"].get("rookie", 0)

    for k in profile["auto_keywords"]:
        if k in text:
            score += profile["weights"].get("auto", 0)

    for k in profile["patch_keywords"]:
        if k in text:
            score += profile["weights"].get("patch", 0)

    for k in profile["insert_keywords"]:
        if k in text:
            score += profile["weights"].get("insert", 0)

    for k in profile["variation_keywords"]:
        if k in text:
            score += profile["weights"].get("variation", 0)

    return score

cards = []
for sheet in xls.sheet_names:
    df = xls.parse(sheet)
    if team_col in df.columns:
        df = df[[team_col]].copy()
        df["score"] = df.apply(score_row, axis=1)
        cards.append(df)

cards_df = pd.concat(cards)
team_strength = cards_df.groupby(team_col)["score"].sum().reset_index()
team_strength.columns = ["Team", "RawScore"]
team_strength["DemandPct"] = team_strength["RawScore"] / team_strength["RawScore"].sum() * 100
team_strength = team_strength.sort_values("DemandPct", ascending=False)

st.success("Checklist parsed and team demand calculated.")

# =================================================
# PRICING INPUTS
# =================================================
st.header("Pricing Inputs")

case_cost = st.number_input("Case cost (direct)", value=800.0, step=25.0)
market_price = st.number_input("Public sealed price (D&A / Blowout)", value=1700.0, step=25.0)
fees = st.slider("Platform + processing fees (%)", 0, 20, 10)
margin = st.slider("Target margin (%)", 0, 60, 30)

net_floor = case_cost * (1 + fees / 100)
target_total = net_floor * (1 + margin / 100)

# =================================================
# PRICING CURVES
# =================================================
def apply_curve(weights, total, mode):
    if mode == "Aggressive":
        adj = weights ** 1.35
    elif mode == "Smoothed":
        adj = weights ** 0.85
    else:
        adj = weights

    pct = adj / adj.sum()
    prices = pct * total
    return (pct * 100).round(2), prices.round(2)

# =================================================
# OUTPUT
# =================================================
st.header("Per-Team Pricing")

for mode in ["Aggressive", "Balanced", "Smoothed"]:
    pct, prices = apply_curve(team_strength["DemandPct"], target_total, mode)
    df = team_strength.copy()
    df["Weight %"] = pct.values
    df["Price ($)"] = prices.values

    st.subheader(f"{mode} Strategy")
    st.dataframe(
        df[["Team", "Weight %", "Price ($)"]].sort_values("Price ($)", ascending=False),
        use_container_width=True
    )

st.caption(
    "Aggressive = top-heavy PYT | Balanced = fair market | Smoothed = fill-friendly. "
    "All pricing sums exactly to target revenue."
)
