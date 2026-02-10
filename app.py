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
st.caption("Uses Beckett checklist team data directly (no roster file needed)")

# =========================================================
# BREAK INPUTS
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
# UPLOAD BECKETT CHECKLIST
# =========================================================
st.subheader("Upload Beckett Checklist (Excel)")

file = st.file_uploader(
    "Upload checklist (.xlsx)",
    type=["xlsx"]
)

if not file:
    st.stop()

# Read Full Checklist sheet explicitly
try:
    df = pd.read_excel(file, sheet_name="Full Checklist")
except Exception:
    st.error("Could not find 'Full Checklist' sheet in the file.")
    st.stop()

# =========================================================
# NORMALIZE COLUMNS
# =========================================================
df.columns = [str(c).strip().lower() for c in df.columns]

# Expected structure from Beckett
# player column usually unnamed or first text column
player_col = df.columns[1]
team_col = df.columns[2]
notes_col = df.columns[3]

df = df[[player_col, team_col, notes_col]]
df.columns = ["player", "team", "notes"]

df["player"] = df["player"].astype(str).str.strip()
df["team"] = df["team"].astype(str).str.strip()
df["notes"] = df["notes"].astype(str).str.strip()

# =========================================================
# FILTER INVALID ROWS
# =========================================================
df = df[
    (df["player"] != "") &
    (~df["player"].str.contains("nan", case=False)) &
    (df["team"] != "")
]

# =========================================================
# TAG HOBBY SIGNALS
# =========================================================
df["rookie"] = df["notes"].str.contains(r"\bRC\b", flags=re.I, regex=True)
df["team_card"] = df["notes"].str.contains("team card", flags=re.I, regex=True)
df["league_leaders"] = df["notes"].str.contains("league leaders", flags=re.I, regex=True)
df["combo"] = df["notes"].str.contains("combo", flags=re.I, regex=True)

# =========================================================
# CHASE SCORING (FANATICS-STYLE)
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
# AGGREGATE BY TEAM
# =========================================================
team_scores = (
    df.groupby("team")["score"]
    .sum()
    .sort_values(ascending=False)
)

total_score = team_scores.sum()

pricing = team_scores.reset_index()
pricing.columns = ["team", "team_score"]

pricing["weight_pct"] = pricing["team_score"] / total_score
pricing["raw_price"] = pricing["weight_pct"] * total_break_price

# =========================================================
# ROUNDING & FLOORS
# =========================================================
pricing["suggested_price"] = (
    pricing["raw_price"]
    .round(-1)
    .clip(lower=floor_price)
)

# Normalize back to total
diff = total_break_price - pricing["suggested_price"].sum()
if abs(diff) >= 10:
    pricing.loc[0, "suggested_price"] += diff

# =========================================================
# OUTPUT
# =========================================================
st.subheader("Suggested PYT Pricing (Beckett-Based)")

st.dataframe(
    pricing.sort_values("suggested_price", ascending=False),
    use_container_width=True
)

st.success("Pricing generated using Beckett team assignments. Copy directly into Fanatics.")

