import streamlit as st
import pandas as pd

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(
    page_title="Headline Break Pricing",
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
# LOAD EXCEL SAFELY
# =========================================================
try:
    raw_df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error("Failed to read the uploaded Excel file.")
    st.exception(e)
    st.stop()

if raw_df.empty:
    st.error("The uploaded file contains no data.")
    st.stop()

# =========================================================
# NORMALIZE COLUMN HEADERS (CRITICAL FIX)
# =========================================================
raw_df.columns = [
    str(col).strip().lower() if col is not None else ""
    for col in raw_df.columns
]

# =========================================================
# COLUMN DETECTION
# =========================================================
def find_column(keywords):
    for col in raw_df.columns:
        for keyword in keywords:
            if keyword in col:
                return col
    return None

team_col = find_column(["team"])
player_col = find_column(["player", "name"])
card_col = find_column(["card", "description", "card name"])

# =========================================================
# VALIDATION
# =========================================================
missing_columns = []

if team_col is None:
    missing_columns.append("Team")
if player_col is None:
    missing_columns.append("Player")
if card_col is None:
    missing_columns.append("Card Description")

if missing_columns:
    st.error(
        "Missing required columns in checklist:\n\n"
        + "\n".join(f"- {c}" for c in missing_columns)
        + "\n\nPlease verify the Beckett checklist format."
    )
    st.stop()

# =========================================================
# CLEAN & STANDARDIZE DATA
# =========================================================
df = raw_df[[team_col, player_col, card_col]].copy()

df.rename(
    columns={
        team_col: "team",
        player_col: "player",
        card_col: "card"
    },
    inplace=True
)

# Drop rows that are fully empty
df = df.dropna(how="all")

# Drop rows without a team value
df = df[df["team"].astype(str).str.strip() != ""]

# Reset index
df.reset_index(drop=True, inplace=True)

# =========================================================
# SUCCESS STATE
# =========================================================
st.success("Checklist uploaded and parsed successfully.")

st.subheader("Parsed Checklist Preview")
st.dataframe(df.head(50), use_container_width=True)

st.caption(
    f"Rows loaded: {len(df)} | "
    f"Teams detected: {df['team'].nunique()} | "
    f"Sport: {sport}"
)

# =========================================================
# END OF CURRENT FUNCTIONALITY
# =========================================================
st.divider()
st.info(
    "Checklist ingestion complete.\n\n"
    "This is the stable foundation. Pricing logic will be layered next."
)
