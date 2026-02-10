import streamlit as st
import pandas as pd
import numpy as np

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(
    page_title="Headline Break Pricing Tool",
    layout="centered"
)

st.title("Headline Break Pricing Tool")

# =========================================================
# PRODUCT CONTEXT
# =========================================================
st.subheader("Product Context")

sport = st.selectbox(
    "Select sport / category",
    ["Baseball (MLB)", "Basketball (NBA)", "Football (NFL)"],
    index=0
)

st.divider()

# =========================================================
# CHECKLIST UPLOAD
# =========================================================
st.subheader("Checklist Upload (Strongly Recommended)")

uploaded_file = st.file_uploader(
    "Upload Beckett Checklist (Excel)",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Please upload a Beckett checklist to continue.")
    st.stop()

# =========================================================
# LOAD RAW EXCEL (NO HEADER ASSUMPTIONS)
# =========================================================
try:
    raw_df = pd.read_excel(uploaded_file, header=None)
except Exception as e:
    st.error("Failed to read Excel file.")
    st.exception(e)
    st.stop()

st.caption("Raw shape:")
st.write(raw_df.shape)

# =========================================================
# IDENTIFY PRIMARY TEXT COLUMN (PLAYERS)
# =========================================================
def text_ratio(col):
    return col.astype(str).str.contains(r"[A-Za-z]", regex=True).mean()

text_ratios = raw_df.apply(text_ratio)
player_col_idx = text_ratios.idxmax()

player_series = raw_df[player_col_idx].astype(str).str.strip()

# =========================================================
# IDENTIFY CARD NUMBER COLUMN (MOSTLY NUMERIC)
# =========================================================
def numeric_ratio(col):
    return pd.to_numeric(col, errors="coerce").notna().mean()

numeric_ratios = raw_df.apply(numeric_ratio)
card_col_idx = numeric_ratios.idxmax()

card_series = raw_df[card_col_idx]

# =========================================================
# BUILD DATAFRAME
# =========================================================
df = pd.DataFrame({
    "player_raw": player_series,
    "card_number": pd.to_numeric(card_series, errors="coerce")
})

# =========================================================
# CLEAN PLAYERS
# =========================================================
df["player"] = (
    df["player_raw"]
    .str.replace(",", "", regex=False)
    .str.strip()
)

# Remove garbage rows
df = df[
    (df["player"].notna()) &
    (df["player"] != "") &
    (~df["player"].str.lower().isin([
        "base set", "nan"
    ])) &
    (~df["player"].str.contains("royals|yankees|dodgers|sox|mets", case=False))
]

df = df[df["card_number"].notna()]

df.reset_index(drop=True, inplace=True)

# =========================================================
# SUCCESS
# =========================================================
st.success("Checklist successfully parsed.")

st.subheader("Parsed Checklist Preview")
st.dataframe(
    df[["player", "card_number"]].head(50),
    use_container_width=True
)

st.caption(
    f"Rows loaded: {len(df)} | "
    f"Unique players: {df['player'].nunique()} | "
    f"Sport: {sport}"
)

# =========================================================
# END v3
# =========================================================
st.divider()
st.info(
    "Structure-aware ingestion complete.\n\n"
    "Player extraction is now reliable. Team mapping comes next."
)
