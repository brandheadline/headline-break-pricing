import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Headline Break Pricing Engine v2",
    layout="centered"
)

st.title("Headline Break Pricing Engine")
st.caption("Fit-to-sell pricing. Checklist-aware. No guessing.")

# =========================================================
# CHECKLIST UPLOAD
# =========================================================

st.header("Checklist Upload (Optional but Recommended)")

uploaded_file = st.file_uploader(
    "Upload Beckett Checklist (Excel)",
    type=["xlsx"]
)

team_strength_df = None
ev_concentration = None
auto_checklist_strength = None
auto_format_recommendation = None

if uploaded_file is not None:
    try:
        xls = pd.ExcelFile(uploaded_file)

        if "Teams" not in xls.sheet_names:
            st.error("Checklist must contain a sheet named 'Teams'.")
        else:
            teams_df = pd.read_excel(xls, sheet_name="Teams")

            # --- HARDEN COLUMN HANDLING ---
            teams_df.columns = [str(c).strip().lower() for c in teams_df.columns]

            if "team" not in teams_df.columns:
                st.error("The 'Teams' sheet must contain a column named 'Team'.")
            else:
                # Remove blank or malformed rows
                teams_df = teams_df.dropna(subset=["team"])

                # Normalize team names
                teams_df["team"] = teams_df["team"].astype(str).str.strip()

                # Count appearances
                team_counts = (
                    teams_df["team"]
                    .value_counts()
                    .reset_index()
                )
                team_counts.columns = ["Team", "Appearances"]

                total_appearances = team_counts["Appearances"].sum()
                team_counts["Weight"] = team_counts["Appearances"] / total_appearances

                # EV concentration = top 5 teams
                ev_concentration = team_counts.head(5)["Weight"].sum()

                # Team strength classification (buyer-perceived ROI)
                def classify_team(weight):
                    if weight >= 0.06:
                        return "Strong"
                    elif weight >= 0.035:
                        return "Average"
                    else:
                        return "Weak"

                team_counts["Team Strength"] = team_counts["Weight"].apply(classify_team)

                team_strength_df = team_counts.sort_values(
                    "Weight", ascending=False
                )

                # Checklist + format inference
                if ev_concentration >= 0.40:
                    auto_checklist_strength = "Elite"
                    auto_format_recommendation = "PYT"
                elif ev_concentration >= 0.30:
                    auto_checklist_strength = "Strong"
                    auto_format_recommendation = "PYT"
                elif ev_concentration >= 0.22:
                    auto_checklist_strength = "Average"
                    auto_format_recommendation = "Random"
                else:
                    auto_checklist_strength = "Weak"
                    auto_format_recommendation = "Divisional"

                st.success("Checklist parsed successfully.")

    except Exception as e:
        st.error(f"Checklist upload error: {e}")

# =========================================================
# PRICING INPUTS
# =========================================================

st.header("Pricing Inputs")

case_cost = st.number_input(
    "Your case cost (Topps direct)",
    min_value=0.0,
    value=800.0,
    step=50.0
)

sealed_anchor = st.number_input(
    "Public sealed price (Dave & Adam’s / Blowout)",
    min_value=0.0,
    value=1700.0,
    step=50.0
)

platform_fees = st.slider(
    "Platform + processing fees (%)",
    min_value=0,
    max_value=20,
    value=10
) / 100

target_margin = st.slider(
    "Target margin (%)",
    min_value=0,
    max_value=50,
    value=30
) / 100

st.divider()

# Auto-set but override-able
checklist_strength = st.selectbox(
    "Checklist strength",
    ["Elite", "Strong", "Average", "Weak"],
    index=["Elite", "Strong", "Average", "Weak"].index(auto_checklist_strength)
    if auto_checklist_strength else 1
)

break_format = st.selectbox(
    "Break format",
    ["PYT", "Random", "Divisional"],
    index=["PYT", "Random", "Divisional"].index(auto_format_recommendation)
    if auto_format_recommendation else 0
)

# =========================================================
# MULTIPLIERS
# =========================================================

checklist_multiplier_map = {
    "Elite": 1.15,
    "Strong": 1.05,
    "Average": 1.00,
    "Weak": 0.90
}

format_multiplier_map = {
    "PYT": 1.05,
    "Random": 1.00,
    "Divisional": 0.97
}

checklist_multiplier = checklist_multiplier_map[checklist_strength]
format_multiplier = format_multiplier_map[break_format]

# =========================================================
# CORE PRICING MATH
# =========================================================

def revenue_for_margin(cost, margin, fees):
    return cost / (1 - margin - fees)

floor = revenue_for_margin(case_cost, 0.0, platform_fees)
safe = revenue_for_margin(case_cost, 0.20, platform_fees)
target = revenue_for_margin(case_cost, target_margin, platform_fees)
stretch = revenue_for_margin(case_cost, 0.40, platform_fees)

safe_adj = safe * checklist_multiplier * format_multiplier
target_adj = target * checklist_multiplier * format_multiplier
stretch_adj = stretch * checklist_multiplier * format_multiplier

sealed_ceiling = sealed_anchor * 1.15

# =========================================================
# OUTPUT
# =========================================================

st.header("Pricing Output")

pricing_df = pd.DataFrame({
    "Tier": [
        "Floor (Do Not Run Below)",
        "Safe",
        "Target",
        "Stretch"
    ],
    "Total Break Revenue ($)": [
        round(floor, 2),
        round(safe_adj, 2),
        round(target_adj, 2),
        round(stretch_adj, 2)
    ]
})

st.table(pricing_df)

# =========================================================
# SANITY CHECKS
# =========================================================

st.header("Sanity Checks")

if target_adj > sealed_ceiling:
    st.warning(
        "Target pricing exceeds sealed market tolerance. "
        "Only justified with strong demand."
    )
else:
    st.success("Target pricing is within sealed market tolerance.")

if checklist_strength == "Weak" and break_format == "PYT":
    st.warning(
        "Weak checklist with PYT is high risk. "
        "Random or Divisional recommended."
    )

if safe_adj < case_cost:
    st.error("Safe pricing does not cover cost. Do not run this break.")

if ev_concentration is not None:
    st.info(
        f"EV Concentration (Top 5 Teams): {round(ev_concentration * 100, 1)}%"
    )

# =========================================================
# TEAM STRENGTH OUTPUT
# =========================================================

if team_strength_df is not None:
    st.header("Team Strength (Customer ROI Signal)")
    st.dataframe(
        team_strength_df[
            ["Team", "Team Strength", "Appearances", "Weight"]
        ],
        use_container_width=True
    )

st.caption(
    "This engine models buyer-perceived value and pricing psychology, "
    "not exact card EV. It is designed to prevent irrational pricing "
    "and bad break structures."
)
