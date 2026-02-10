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
st.caption("Floor-first, weight-based PYT pricing (Fanatics-style)")

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
# UPLOAD BECKETT CHECKLIST
# =========================================================
st.subheader("Upload Beckett Checklist (Excel)")

file = st.file_uploader(
    "Upload checklist (.xlsx)",
    type=["xlsx"]
)

if not file:
    st.stop()

# Load Full Checklist
df = pd.read_excel(file, sheet_name="Full Checklist")
df.columns = [str(c).strip().lower() for c in df.columns]

# Assume Beckett structure
df = df.iloc[:, 1:4]
df.columns = ["player", "team", "notes"]

df["player"] = df["player"].astype(str).str.strip()
df["team"] = df["team"].astype(str).str.strip()
df["notes"] = df["notes"].astype(str).str.strip()

# Remove junk rows
df = df[
    (df["player"] != "") &
    (~df["player"].str.contains("nan", case=False)) &
    (df["team"] != "")
]

# =========================================================
# TAG HOBBY SIGNALS
# =========================================================
df["rookie"] = df["notes"].str.contains(r"\bRC\b", flags=re.I, regex=True)
df["league_leaders"] = df["notes"].str.contains("league leaders", flags=re.I, regex=True)
df["combo"] = df["notes"].str.contains("combo", flags=re.I, regex=True)
df["team_card"] = df["notes"].str.contains("team card", flags=re.I, regex=True)

# =========================================================
# CHASE SCORING
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
team_scores = df.groupby("team")["score"].sum().sort_values(ascending=False)
teams = team_scores.reset_index()
teams.columns = ["team", "team_score"]

num_teams = len(teams)

# =========================================================
# FLOOR-FIRST PRICING (CORRECT LOGIC)
# =========================================================
floor_total = num_teams * floor_price
remaining_pool = total_break_price - floor_total

if remaining_pool <= 0:
    st.error("Floor price too high for total break price.")
    st.stop()

total_score = teams["team_score"].sum()
teams["weight_pct"] = teams["team_score"] / total_score
teams["variable_price"] = teams["weight_pct"] * remaining_pool
teams["suggested_price"] = floor_price + teams["variable_price"]

# Hobby rounding
teams["suggested_price"] = teams["suggested_price"].round(-1)

# Final reconciliation (rounding only, safe)
rounding_diff = total_break_price - teams["suggested_price"].sum()
teams.loc[0, "suggested_price"] += rounding_diff

# =========================================================
# OUTPUT
# =========================================================
st.subheader("Suggested PYT Pricing (Corrected)")

st.dataframe(
    teams.sort_values("suggested_price", ascending=False),
    use_container_width=True
)

st.success("Pricing generated using floor-first allocation. No negatives possible.")
