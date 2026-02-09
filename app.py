import streamlit as st
import pandas as pd

st.set_page_config(page_title="Headline Break Pricing Engine", layout="centered")

st.title("Headline Break Pricing Engine")
st.caption("Fit-to-sell pricing. No guessing. No copying competitors.")

# -----------------------------
# INPUTS
# -----------------------------

st.header("Inputs")

case_cost = st.number_input(
    "Your case cost (Topps direct)",
    min_value=0.0,
    value=2500.0,
    step=100.0
)

sealed_anchor = st.number_input(
    "Public sealed price (Dave & Adam’s / Blowout)",
    min_value=0.0,
    value=3200.0,
    step=100.0
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

checklist_tier = st.selectbox(
    "Checklist strength",
    ["Elite", "Strong", "Average", "Weak"]
)

format_type = st.selectbox(
    "Break format",
    ["PYT", "Random", "Divisional"]
)

# -----------------------------
# MULTIPLIERS
# -----------------------------

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

checklist_multiplier = checklist_multiplier_map[checklist_tier]
format_multiplier = format_multiplier_map[format_type]

# -----------------------------
# CORE MATH
# -----------------------------

def revenue_for_margin(cost, margin, fees):
    return cost / (1 - margin - fees)

floor_revenue = revenue_for_margin(case_cost, 0.0, platform_fees)
safe_revenue = revenue_for_margin(case_cost, 0.20, platform_fees)
target_revenue = revenue_for_margin(case_cost, target_margin, platform_fees)
stretch_revenue = revenue_for_margin(case_cost, 0.40, platform_fees)

adjusted_safe = safe_revenue * checklist_multiplier * format_multiplier
adjusted_target = target_revenue * checklist_multiplier * format_multiplier
adjusted_stretch = stretch_revenue * checklist_multiplier * format_multiplier

sealed_ceiling = sealed_anchor * 1.15

# -----------------------------
# OUTPUT
# -----------------------------

st.header("Pricing Output")

pricing_table = pd.DataFrame({
    "Tier": ["Floor (Do Not Run Below)", "Safe", "Target", "Stretch"],
    "Total Break Revenue ($)": [
        round(floor_revenue, 2),
        round(adjusted_safe, 2),
        round(adjusted_target, 2),
        round(adjusted_stretch, 2)
    ]
})

st.table(pricing_table)

# -----------------------------
# WARNINGS
# -----------------------------

st.header("Sanity Checks")

if adjusted_target > sealed_ceiling:
    st.warning(
        "Target pricing exceeds typical sealed tolerance. "
        "Only justified if demand is extremely strong."
    )
else:
    st.success("Target pricing is within sealed market tolerance.")

if checklist_tier == "Weak" and format_type == "PYT":
    st.warning(
        "Weak checklist with PYT is risky. Random or Divisional may sell better."
    )

if adjusted_safe < case_cost:
    st.error("Safe price does not cover cost. Do not run this break.")

st.caption(
    "This tool provides pricing bands, not a single price. "
    "You still choose how aggressive you want to be."
)
