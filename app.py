import streamlit as st
import pandas as pd

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
# LOAD EXCEL
# =========================================================
try:
    raw_df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error("Failed to read Excel file.")
    st.exception(e)
    st.stop()

if raw_df.empty:
    st.error("Uploaded file contains no data.")
    st.stop()

# =========================================================
# NORMALIZE HEADERS (CRITICAL)
# =========================================================
raw_df.columns = [
    str(col).strip().lower() if col is not None else ""
    for col in raw_df.columns
]

st.caption("Detected columns:")
st.write(list(raw_df.columns))

# =========================================================
# COLUMN DETECTION (BECKETT-AWARE)
# =========================================================
def find_column(keywords):
    for col in raw_df.columns:
        for keyword in keywords:
            if keyword in col:
                return col
    return None

player_col = find_column(["player", "name"])
card_number_col = find_column(["card #", "card#", "#"])
set_col = find_column(["set"])
notes_col = find_column(["note", "variation", "parallel"])

# =========================================================
# VALIDATION (ONLY REQUIRE WHAT EXISTS IN BECKETT)
# =========================================================
if player_col is None:
    st.error(
        "Missing required column: Player\n\n"
        "Beckett checklists must contain a Player column."
    )
    st.stop()

# =========================================================
# BUILD CLEAN DATAFRAME
# =========================================================
df = pd.DataFrame()
df["player"] = raw_df[player_col].astype(str).str.strip()

# Optional columns
df["card_number"] = (
    raw_df[card_number_col].astype(str).str.strip()
    if card_number_col else ""
)

df["set"] = (
    raw_df[set_col].astype(str).str.strip()
    if set_col else ""
)

df["notes"] = (
    raw_df[notes_col].astype(str).str.strip()
    if notes_col else ""
)

# =========================================================
# CONSTRUCT CARD DESCRIPTION (CANONICAL)
# =========================================================
def build_card_description(row):
    parts = []
    if row["set"]:
        parts.append(row["set"])
    if row["card_number"]:
        parts.append(f"#{row['card_number']}")
    if row["notes"]:
        parts.append(row["notes"])
    return " – ".join(parts)

df["card"] = df.apply(build_card_description, axis=1)

# Placeholder for team (mapped later)
df["team"] = ""

# =========================================================
# CLEAN ROWS
# =========================================================
df = df[df["player"] != ""]
df.reset_index(drop=True, inplace=True)

# =========================================================
# SUCCESS STATE
# =========================================================
st.success("Checklist successfully ingested.")

st.subheader("Parsed Checklist Preview")
st.dataframe(
    df[["player", "card"]].head(50),
    use_container_width=True
)

st.caption(
    f"Rows loaded: {len(df)} | "
    f"Unique players: {df['player'].nunique()} | "
    f"Sport: {sport}"
)

# =========================================================
# END OF CURRENT SCOPE
# =========================================================
st.divider()
st.info(
    "Checklist ingestion complete.\n\n"
    "Team assignment and pricing logic will be layered next."
)
