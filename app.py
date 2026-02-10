import streamlit as st
import pandas as pd

# -----------------------------
# APP CONFIG
# -----------------------------
st.set_page_config(
    page_title="Headline Break Pricing",
    layout="centered"
)

st.title("Product Context")

# -----------------------------
# PRODUCT CONTEXT
# -----------------------------
sport = st.selectbox(
    "Select sport / category",
    options=["Baseball (MLB)", "Basketball (NBA)", "Football (NFL)"],
    index=0
)

st.divider()

# -----------------------------
# CHECKLIST UPLOAD
# -----------------------------
st.subheader("Checklist Upload (Strongly Recommended)")

uploaded_file = st.file_uploader(
    "Upload Beckett Checklist (Excel)",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Upload a Beckett checklist to continue.")
    st.stop()

# -----------------------------
# LOAD EXCEL SAFELY
# -----------------------------
try:
    teams_df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error("❌ Failed to read Excel file.")
    st.exception(e)
    st.stop()

# -----------------------------
# VALIDATE DATAFRAME
# -----------------------------
if teams_df.empty:
    st.error("❌ Uploaded file is empty.")
    st.stop()

# -----------------------------
# NORMALIZE COLUMN HEADERS
# -----------------------------
teams_df.columns = (
    teams_df.columns
    .map(lambda x: str(x).strip().lower() if x is not None else "")
)

# Debug visibility (leave this in for now)
st.write("Detected columns:", list(teams_df.columns))

# -----------------------------
# REQUIRED COLUMN DETECTION
# -----------------------------
def find_column(keyword_list):
    for col in teams_df.columns:
        for keyword in keyword_list:
            if keyword in col:
                return col
    return None

team_col = find_column(["team"])
player_col = find_column(["player", "name"])
card_col = find_column(["card", "description", "card name"])

# -----------------------------
# HARD FAIL IF REQUIRED DATA IS MISSING
# -----------------------------
missing = []

if team_col is None:
    missing.append("Team")
if player_col is None:
    missing.append("Player")
if card_col is None:
    missing.append("Card Description")

if missing:
    st.error(
        "❌ Missing required columns:\n\n"
        + "\n".join([f"- {m}" for m in missing])
        + "\n\nPlease verify the Beckett checklist format."
    )
    st.stop()

# -----------------------------
# CLEAN CORE DATA
# -----------------------------
core_df = teams_df[[team_col, player_col, card_col]].copy()

core_df.rename(
    columns={
        team_col: "team",
        player_col: "player",
        card_col: "card"
    },
    inplace=True
)

# Drop garbage rows
core_df = core_df.dropna(how="all")
core_df = core_df[core_df["team"].astype(str).str.len() > 0]

# -----------------------------
# SUCCESS STATE
# -----------------------------
st.success("✅ Checklist loaded successfully")

st.subheader("Preview")
st.dataframe(core_df.head(25), use_container_width=True)

# -----------------------------
# NEXT STEP PLACEHOLDER
# -----------------------------
st.divider()
st.subheader("Next Step")
st.info(
    "Checklist successfully parsed.\n\n"
    "Break pricing logic will attach here next."
)
