import streamlit as st
import pandas as pd
import re

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(page_title="Break Pricing Engine", layout="centered")
st.title("Break Pricing Engine")

# =========================================================
# PRODUCT INPUTS
# =========================================================
st.subheader("Product Inputs")

product_name = st.text_input("Product Name", "2026 Topps Baseball Hobby")

col1, col2 = st.columns(2)
box_cost = col1.number_input("Cost per Box ($)", min_value=0.0, value=150.0)
num_boxes = col2.number_input("Number of Boxes", min_value=1, value=6)

col3, col4 = st.columns(2)
platform_fee_pct = col3.number_input("Platform Fee (%)", value=10.0)
target_margin_pct = col4.number_input("Target Margin (%)", value=20.0)

st.divider()

# =========================================================
# CHECKLIST UPLOAD
# =========================================================
st.subheader("Upload Checklist (Beckett Excel)")

file = st.file_uploader("Upload Excel", type=["xlsx"])

if not file:
    st.stop()

raw = pd.read_excel(file, header=None)

# =========================================================
# FLATTEN TO TEXT ROWS (FANATICS STYLE)
# =========================================================
rows = raw.astype(str).apply(lambda r: " ".join(r.values), axis=1)

df = pd.DataFrame({"text": rows})

# =========================================================
# SIGNAL TAGGING (OPINIONATED + SIMPLE)
# =========================================================
def has(pattern):
    return df["text"].str.contains(pattern, flags=re.IGNORECASE, regex=True)

df["rookie"] = has(r"\bRC\b|rookie")
df["auto"] = has(r"auto|autograph")
df["patch"] = has(r"patch|relic|memorabilia")
df["dual"] = has(r"dual|combo")
df["legend"] = has(r"hall of fame|hof|legend")

df["rpa"] = df["rookie"] & df["auto"] & df["patch"]

# =========================================================
# PLAYER EXTRACTION (GOOD ENOUGH, NOT PERFECT)
# =========================================================
def extract_player(text):
    m = re.findall(r"[A-Z][a-z]+ [A-Z][a-z]+", text)
    return m[0] if m else None

df["player"] = df["text"].apply(extract_player)

# =========================================================
# SIGNAL COUNTS
# =========================================================
summary = {
    "Total Autos": int(df["auto"].sum()),
    "Rookie Autos": int((df["rookie"] & df["auto"]).sum()),
    "RPAs": int(df["rpa"].sum()),
    "Dual Autos": int(df["dual"].sum()),
    "Legend Autos": int(df["legend"].sum())
}

st.subheader("Checklist Signal Summary")
st.json(summary)

# =========================================================
# PLAYER CHASE SCORING (THIS IS THE SECRET SAUCE)
# =========================================================
def score_row(r):
    score = 0
    if r["rookie"] and r["auto"]: score += 5
    if r["rpa"]: score += 7
    if r["dual"]: score += 4
    if r["legend"]: score += 3
    if r["auto"]: score += 2
    return score

df["score"] = df.apply(score_row, axis=1)

player_scores = (
    df.dropna(subset=["player"])
      .groupby("player")["score"]
      .sum()
      .sort_values(ascending=False)
)

st.subheader("Top Chase Players")
st.dataframe(player_scores.head(15))

# =========================================================
# PRODUCT STRENGTH SCORE
# =========================================================
strength_score = player_scores.sum()

st.metric("Product Strength Score", int(strength_score))

# =========================================================
# BREAK PRICE CALCULATION (FANATICS LOGIC)
# =========================================================
total_cost = box_cost * num_boxes
fee_multiplier = 1 + (platform_fee_pct / 100)
margin_multiplier = 1 + (target_margin_pct / 100)

suggested_break_price = total_cost * fee_multiplier * margin_multiplier

st.subheader("Suggested Break Economics")

st.metric("Total Cost", f"${total_cost:,.2f}")
st.metric("Suggested Break Price", f"${suggested_break_price:,.2f}")

# =========================================================
# TEAM BUCKETING (SIMPLIFIED PYT FRAMEWORK)
# =========================================================
st.subheader("PYT Team Buckets (Framework)")

st.markdown("""
**Tier 1 (Top Chases)**  
• Teams with top 3–5 scored players  
• Price aggressively  

**Tier 2 (Mid)**  
• Teams with at least one meaningful hit  
• Price to move  

**Floor Teams**  
• No major autos or rookies  
• Used to balance room  

This mirrors how professional breakers structure PYT.
""")

st.success("Pricing framework generated. Adjust final numbers with market sanity check.")
