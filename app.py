import streamlit as st
import pandas as pd
import numpy as np

# -------------------------------------------------
# PAGE SETUP
# -------------------------------------------------

st.set_page_config(
    page_title="Headline Break Pricing Engine v2.5",
    layout="centered"
)

st.title("Headline Break Pricing Engine")
st.caption("Checklist-aware. Rookie-driven. No guessing.")

# -------------------------------------------------
# OFFICIAL MLB TEAMS
# -------------------------------------------------

MLB_TEAMS = [
    "Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox",
    "Chicago Cubs","Chicago White Sox","Cincinnati Reds","Cleveland Guardians",
    "Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals",
    "Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers",
    "Minnesota Twins","New York Mets","New York Yankees","Oakland Athletics",
    "Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres","San Francisco Giants",
    "Seattle Mariners","St. Louis Cardinals","Tampa Bay Rays","Texas Rangers",
    "Toronto Blue Jays","Washington Nationals"
]

# -------------------------------------------------
# CARD TYPE WEIGHTS (DEMAND LOGIC)
# -------------------------------------------------

CARD_WEIGHTS = {
    "rookie patch auto": 10,
    "rookie autograph": 6,
    "rookie auto": 6,
    "autograph": 5,
    "patch": 4,
    "relic": 4,
    "insert": 3,
    "variation": 3,
    "rookie": 1,
    "base": 0.5
}

# -------------------------------------------------
# CHECKLIST INGESTION
# -------------------------------------------------

st.header("Checklist Upload (Strongly Recommended)")

uploaded_file = st.file_uploader(
    "Upload Beckett Checklist (Excel)",
    type=["xlsx"]
)

team_structural_df = None
rookie_df = None
final_team_df = None

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        all_text = []

        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet, header=None)
            all_text.extend(df.astype(str).values.flatten())

        # -------------------------------------------------
        # STRUCTURAL TEAM SHARE
        # -------------------------------------------------

        team_counts = {team: 0 for team in MLB_TEAMS}

        for value in all_text:
            for team in MLB_TEAMS:
                if value.strip() == team:
                    team_counts[team] += 1

        team_df = pd.DataFrame(
            [(k, v) for k, v in team_counts.items() if v > 0],
            columns=["Team", "Appearances"]
        )

        total_appearances = team_df["Appearances"].sum()
        team_df["Checklist Share (%)"] = (
            team_df["Appearances"] / total_appearances * 100
        ).round(2)

        def structural_tier(pct):
            if pct >= 6:
                return "Strong"
            elif pct >= 3.5:
                return "Average"
            else:
                return "Weak"

        team_df["Structural Tier"] = team_df["Checklist Share (%)"].apply(structural_tier)

        # -------------------------------------------------
        # ROOKIE DETECTION + PREMIUM SCORING
        # -------------------------------------------------

        rookie_scores = {}

        for value in all_text:
            text = value.lower()

            if "rc" in text or "rookie" in text:
                weight = 0

                for key, score in CARD_WEIGHTS.items():
                    if key in text:
                        weight = max(weight, score)

                for team in MLB_TEAMS:
                    if team.lower() in text:
                        rookie_scores.setdefault(team, 0)
                        rookie_scores[team] += weight

        rookie_df = pd.DataFrame(
            [(k, v) for k, v in rookie_scores.items()],
            columns=["Team", "Rookie Impact Score"]
        ).sort_values("Rookie Impact Score", ascending=False)

        # -------------------------------------------------
        # ROOKIE TIERS
        # -------------------------------------------------

        def rookie_tier(score):
            if score >= 40:
                return "Elite"
            elif score >= 20:
                return "Strong"
            elif score >= 8:
                return "Moderate"
            else:
                return "None"

        rookie_df["Rookie Tier"] = rookie_df["Rookie Impact Score"].apply(rookie_tier)

        # -------------------------------------------------
        # FINAL TEAM DEMAND TIER (AUTO PROMOTION)
        # -------------------------------------------------

        final_df = team_df.merge(rookie_df, on="Team", how="left")
        final_df["Rookie Impact Score"] = final_df["Rookie Impact Score"].fillna(0)
        final_df["Rookie Tier"] = final_df["Rookie Tier"].fillna("None")

        def final_tier(row):
            if row["Rookie Tier"] == "Elite":
                return "Elite"
            if row["Rookie Tier"] == "Strong":
                return "Strong"
            return row["Structural Tier"]

        final_df["Final Demand Tier"] = final_df.apply(final_tier, axis=1)

        final_team_df = final_df.sort_values(
            ["Final Demand Tier","Checklist Share (%)"],
            ascending=[True, False]
        )

        st.success("Checklist parsed successfully.")

    except Exception as e:
        st.error(f"Checklist processing error: {e}")

# -------------------------------------------------
# PRICING INPUTS
# -------------------------------------------------

st.header("Pricing Inputs")

case_cost = st.number_input("Case cost (Topps direct)", value=800.0, step=50.0)
sealed_anchor = st.number_input("Public sealed price (D&A / Blowout)", value=1700.0, step=50.0)

platform_fees = st.slider("Platform + processing fees (%)", 0, 20, 10) / 100
target_margin = st.slider("Target margin (%)", 0, 50, 30) / 100

break_format = st.selectbox("Break format", ["PYT","Random","Divisional"])

# -------------------------------------------------
# MULTIPLIERS
# -------------------------------------------------

tier_multiplier = {
    "Elite": 1.18,
    "Strong": 1.08,
    "Average": 1.00,
    "Weak": 0.92
}

format_multiplier = {
    "PYT": 1.05,
    "Random": 1.00,
    "Divisional": 0.97
}

# -------------------------------------------------
# PRICING CALC
# -------------------------------------------------

def revenue(cost, margin, fees):
    return cost / (1 - margin - fees)

floor = revenue(case_cost, 0, platform_fees)
safe = revenue(case_cost, 0.20, platform_fees)
target = revenue(case_cost, target_margin, platform_fees)
stretch = revenue(case_cost, 0.40, platform_fees)

tier = "Average"
if final_team_df is not None:
    if "Elite" in final_team_df["Final Demand Tier"].values:
        tier = "Elite"
    elif "Strong" in final_team_df["Final Demand Tier"].values:
        tier = "Strong"

mult = tier_multiplier[tier] * format_multiplier[break_format]

pricing = pd.DataFrame({
    "Tier": ["Floor","Safe","Target","Stretch"],
    "Total Break Revenue ($)": [
        round(floor,2),
        round(safe * mult,2),
        round(target * mult,2),
        round(stretch * mult,2)
    ]
})

st.header("Pricing Output")
st.table(pricing)

# -------------------------------------------------
# TOP ROOKIES
# -------------------------------------------------

if rookie_df is not None and not rookie_df.empty:
    st.header("Top Rookies in This Product")
    st.table(rookie_df.head(3))

# -------------------------------------------------
# TEAM DEMAND TABLE
# -------------------------------------------------

if final_team_df is not None:
    st.header("Team Demand Breakdown")
    st.dataframe(
        final_team_df[
            ["Team","Checklist Share (%)","Structural Tier","Rookie Tier","Final Demand Tier"]
        ],
        use_container_width=True
    )

st.caption(
    "Rookie demand automatically overrides structural team gravity when premium exposure exists."
)
