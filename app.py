import streamlit as st
import pandas as pd
import re

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(
    page_title="PYT Break Pricing Engine",
    layout="centered"
)

st.title("PYT Break Pricing Engine")
st.caption("Fanatics-style pricing framework for breakers")

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

min_team_price = col2.number_input(
    "Floor Team Price ($)",
    value=35,
    step=5
)

st.divider()

# =========================================================
# UPLOAD CHECKLIST
# =========================================================
st.subheader("Checklist Upload (Beckett Excel)")

checklist_file = st.file_uploader(
    "Upload checklist (.xlsx)",
    type=["xlsx"]
)

if not checklist_file:
    st.stop()

# Read raw, no header assumptions
raw = pd.read_excel(checklist_file, header=None)

# Flatten rows into text blobs
rows = raw.astype(str).apply(lambda r: " ".join(r.values), axis=1)
df = pd.DataFrame({"text": rows})

# =========================================================
# SIGNAL TAGGING (HOBBY HEURISTICS)
# =========================================================
def has(pattern):
    return df["text"].str.contains(pattern, flags=re.I, regex=True)

df["rookie"] = has(r"\bRC\b|rookie")
df["auto"] = has(r"auto|autograph")
df["patch"] = has(r"patch|relic|memorabilia")
df["dual"] = has(r"dual|combo")
df["legend"] = has(r"hall of fame|hof|legend")

df["rpa"] = df["rookie"] & df["auto"] & df["patch"]

# =========================================================
# PLAYER EXTRACTION (GOOD-ENOUGH, INDUSTRY STANDARD)
# =========================================================
def extract_player(text):
    m = re.findall(r"[A-Z][a-z]+ [A-Z][a-z]+", text)
    return m[0] if m else None

df["player"] = df["text"].apply(extract_player)
df = df.dropna(subset=["player"])

# =========================================================
# PLAYER CHASE SCORING (OPINIONATED & SIMPLE)
# =========================================================
def chase_score(row):
    score = 0
    if row["rpa"]:
        score += 10
    elif row["rookie"] and row["auto"]:
        score += 7
    elif row["auto"]:
        score += 4

    if row["dual"]:
        score += 3
    if row["legend"]:
        score += 2

    return score

df["score"] = df.apply(chase_score, axis=1)

# =========================================================
# UPLOAD PLAYER → TEAM MAP
# =========================================================
st.subheader("Player → Team Mapping")

team_file = st.file_uploader(
    "Upload player-team mapping (.csv)",
    type=["csv"],
    help="CSV must contain columns: player, team"
)

if not team_file:
    st.stop()

team_map = pd.read_csv(team_file)
team_map.columns = [c.lower().strip() for c in team_map.columns]

if "player" not in team_map.columns or "team" not in team_map.columns:
    st.error("CSV must contain 'player' and 'team' columns.")
    st.stop()

team_map["player"] = team_map["player"].astype(str).str.strip()
team_map["team"] = team_map["team"].astype(str).str.strip()

# Merge
df = df.merge(team_map, on="player", how="left")
df = df.dropna(subset=["team"])

# =========================================================
# TEAM AGGREGATION
# =========================================================
team_scores = (
    df.groupby("team")["score"]
    .sum()
    .sort_values(ascending=False)
)

total_score = team_scores.sum()

pricing = (
    team_scores
    .reset_index()
    .rename(columns={"score": "team_score"})
)

pricing["weight_pct"] = pricing["team_score"] / total_score
pricing["raw_price"] = pricing["weight_pct"] * total_break_price

# =========================================================
# HOBBY ROUNDING & FLOORS
# =========================================================
pricing["suggested_price"] = (
    pricing["raw_price"]
    .round(-1)               # round to nearest $10
    .clip(lower=min_team_price)
)

# Normalize back to total (minor correction)
price_diff = total_break_price - pricing["suggested_price"].sum()
if abs(price_diff) >= 10:
    pricing.loc[0, "suggested_price"] += price_diff

# =========================================================
# OUTPUT
# =========================================================
st.subheader("Suggested PYT Pricing (Copy This)")

st.dataframe(
    pricing[[
        "team",
        "team_score",
        "weight_pct",
        "suggested_price"
    ]].sort_values("suggested_price", ascending=False),
    use_container_width=True
)

st.success("Pricing generated. Use as a sanity check or direct copy for Fanatics PYT.")

# =========================================================
# OPTIONAL INSIGHT
# =========================================================
with st.expander("Why teams are priced this way"):
    st.markdown("""
This pricing reflects **relative chase weight**, not exact EV.

• Teams with elite rookie autos, RPAs, or duals float to the top  
• Mid teams price to move  
• Floor teams stabilize the room  

This mirrors how experienced breakers price quickly and consistently.
""")
