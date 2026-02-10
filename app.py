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

checklist_file = st.file_uploader(
    "Upload Beckett Checklist (Excel)",
    type=["xlsx"],
    key="checklist"
)

if checklist_file is None:
    st.info("Please upload a Beckett checklist to continue.")
    st.stop()

# =========================================================
# LOAD CHECKLIST
# =========================================================
try:
    raw_df = pd.read_excel(checklist_file)
except Exception as e:
    st.error("Failed to read checklist.")
    st.exception(e)
    st.stop()

if raw_df.empty:
    st.error("Checklist is empty.")
    st.stop()

# =========================================================
# NORMALIZE HEADERS
# =========================================================
raw_df.columns = [
    str(col).strip().lower() if col is not None else ""
    for col in raw_df.columns
]

st.caption("Detected checklist columns:")
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

if player_col is None:
    st.error("Checklist must contain a Player column.")
    st.stop()

# =========================================================
# BUILD BASE DATAFRAME
# =========================================================
df = pd.DataFrame()
df["player"] = raw_df[player_col].astype(str).str.strip()

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
# BUILD CARD DESCRIPTION
# =========================================================
def build_card(row):
    parts = []
    if row["set"]:
        parts.append(row["set"])
    if row["card_number"]:
        parts.append(f"#{row['card_number']}")
    if row["notes"]:
        parts.append(row["notes"])
    return " – ".join(parts)

df["card"] = df.apply(build_card, axis=1)

# =========================================================
# CLEAN CHECKLIST DATA
# =========================================================
df = df[df["player"].notna()]
df = df[df["player"] != ""]
df.reset_index(drop=True, inplace=True)

# =========================================================
# CHECKLIST SUCCESS
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

st.divider()

# =========================================================
# PLAYER → TEAM MAPPING
# =========================================================
st.subheader("Player → Team Mapping")

team_file = st.file_uploader(
    "Upload Player-Team Mapping (CSV)",
    type=["csv"],
    help="CSV must contain columns: player, team",
    key="team_map"
)

if team_file is None:
    st.info("Upload a player-to-team mapping to continue.")
    st.stop()

# =========================================================
# LOAD TEAM MAP
# =========================================================
try:
    team_df = pd.read_csv(team_file)
except Exception as e:
    st.error("Failed to read team mapping file.")
    st.exception(e)
    st.stop()

if team_df.empty:
    st.error("Team mapping file is empty.")
    st.stop()

# =========================================================
# NORMALIZE TEAM MAP
# =========================================================
team_df.columns = [
    str(col).strip().lower() if col is not None else ""
    for col in team_df.columns
]

if "player" not in team_df.columns or "team" not in team_df.columns:
    st.error("Team mapping CSV must contain 'player' and 'team' columns.")
    st.stop()

team_df["player"] = team_df["player"].astype(str).str.strip()
team_df["team"] = team_df["team"].astype(str).str.strip()

# =========================================================
# MERGE TEAM DATA
# =========================================================
df = df.merge(
    team_df[["player", "team"]],
    on="player",
    how="left"
)

# =========================================================
# REPORT MATCH RESULTS
# =========================================================
matched = df["team"].notna().sum()
unmatched = df["team"].isna().sum()

st.success("Player-team mapping applied.")

col1, col2 = st.columns(2)
col1.metric("Matched Players", matched)
col2.metric("Unmatched Players", unmatched)

# =========================================================
# SHOW UNMATCHED (IF ANY)
# =========================================================
if unmatched > 0:
    st.warning("Some players were not matched to a team.")
    st.dataframe(
        df[df["team"].isna()][["player"]].drop_duplicates().head(50),
        use_container_width=True
    )

# =========================================================
# FINAL DATA PREVIEW
# =========================================================
st.subheader("Final Dataset Preview")
st.dataframe(
    df[["player", "team", "card"]].head(50),
    use_container_width=True
)

# =========================================================
# END OF v2
# =========================================================
st.divider()
st.info(
    "Player-team mapping complete.\n\n"
    "Team aggregation and pricing logic can now be layered safely."
)
