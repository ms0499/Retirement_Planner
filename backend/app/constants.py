"""
Editable global planning assumptions. These are defaults only — each
household can override any of them (see app/models/assumptions.py).
Edit this file and redeploy to change the defaults for new households.
"""

DEFAULT_INFLATION_RATE = 0.03
DEFAULT_EXPECTED_RETURN = 0.07
DEFAULT_SAFE_WITHDRAWAL_RATE = 0.04

# Total household annual post-retirement spending, by lifestyle preset.
# Used to prefill expense categories during onboarding; fully editable
# afterward via custom expense categories.
LIFESTYLE_PRESET_ANNUAL_SPEND = {
    "modest": 50_000,
    "comfortable": 80_000,
    "luxurious": 120_000,
}

# Default expense category split (fractions of total annual spend above),
# used to prefill onboarding so the user isn't starting from a blank form.
DEFAULT_EXPENSE_CATEGORY_SPLIT = {
    "housing": 0.30,
    "healthcare": 0.15,
    "food": 0.15,
    "travel": 0.10,
    "transportation": 0.10,
    "other": 0.20,
}

DEFAULT_LIFE_EXPECTANCY = 90
DEFAULT_RETIREMENT_AGE = 65

# --- Phase 2: tax & withdrawal intelligence -------------------------------
# 2024 federal ordinary-income brackets: (income threshold, marginal rate),
# ascending. Edit these each year (or add a lookup by year) to stay current.
FEDERAL_TAX_BRACKETS = {
    "single": [
        (0, 0.10),
        (11_600, 0.12),
        (47_150, 0.22),
        (100_525, 0.24),
        (191_950, 0.32),
        (243_725, 0.35),
        (609_350, 0.37),
    ],
    "married_filing_jointly": [
        (0, 0.10),
        (23_200, 0.12),
        (94_300, 0.22),
        (201_050, 0.24),
        (383_900, 0.32),
        (487_450, 0.35),
        (731_200, 0.37),
    ],
}

STANDARD_DEDUCTION = {
    "single": 14_600,
    "married_filing_jointly": 29_200,
}

# Provisional-income thresholds for the simplified IRS worksheet that
# determines how much of Social Security is taxable (0% / up to 50% / up to
# 85%). (lower_threshold, upper_threshold) per filing status.
SOCIAL_SECURITY_TAXABILITY_THRESHOLDS = {
    "single": (25_000, 34_000),
    "married_filing_jointly": (32_000, 44_000),
}

# Required Minimum Distributions start the year a person turns this age
# (SECURE 2.0, for those turning 73 in 2023 or later).
RMD_START_AGE = 73

# IRS Uniform Lifetime Table (Pub. 590-B) — age -> distribution divisor.
# Applied to the prior year-end balance of each person's own tax-deferred
# accounts (401k/Traditional IRA) to get that year's required withdrawal.
RMD_UNIFORM_LIFETIME_TABLE = {
    72: 27.4, 73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0,
    79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7, 84: 16.8, 85: 16.0,
    86: 15.2, 87: 14.4, 88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8,
    93: 10.1, 94: 9.5, 95: 8.9, 96: 8.4, 97: 7.8, 98: 7.3, 99: 6.8,
    100: 6.4, 101: 6.0, 102: 5.6, 103: 5.2, 104: 4.9, 105: 4.6, 106: 4.3,
    107: 4.1, 108: 3.9, 109: 3.7, 110: 3.5, 111: 3.4, 112: 3.3, 113: 3.1,
    114: 3.0, 115: 2.9, 116: 2.8, 117: 2.7, 118: 2.5, 119: 2.3, 120: 2.0,
}

# Social Security claiming-age mechanics. No birthdate is collected (only
# current_age), so — like most simplified planners — we assume everyone's
# Full Retirement Age is 67 (correct for anyone born 1960 or later).
SOCIAL_SECURITY_FULL_RETIREMENT_AGE = 67
SOCIAL_SECURITY_MIN_CLAIM_AGE = 62
SOCIAL_SECURITY_MAX_CLAIM_AGE = 70
# Early-claim reduction: 5/9 of 1% per month for the first 36 months before
# FRA, then 5/12 of 1% per month beyond that.
SOCIAL_SECURITY_EARLY_REDUCTION_RATE_FIRST_36_MONTHS = 5 / 9 / 100
SOCIAL_SECURITY_EARLY_REDUCTION_RATE_ADDITIONAL_MONTHS = 5 / 12 / 100
# Delayed retirement credit: 2/3 of 1% per month (8%/year) after FRA, up to 70.
SOCIAL_SECURITY_DELAYED_CREDIT_RATE_PER_MONTH = 2 / 3 / 100

# Roth conversion suggestions target "filling up" this bracket each year in
# the low-income window between retirement and RMDs starting — a common
# planner heuristic (converting further would jump to the next, much wider
# bracket). Change this to be more/less aggressive.
ROTH_CONVERSION_TARGET_BRACKET_RATE = 0.22

# --- Phase 3: guardrails, healthcare, Monte Carlo -------------------------
# Guyton-Klinger-style dynamic spending guardrails: if the current
# withdrawal rate (this year's lifestyle spending / current portfolio
# balance) drifts too far from the rate set at retirement, spending is
# nudged down (portfolio running hot) or up (portfolio running cold).
# Non-discretionary costs (healthcare) are not touched by guardrails.
GUARDRAILS_UPPER_TRIGGER_PCT = 0.20
GUARDRAILS_LOWER_TRIGGER_PCT = 0.20
GUARDRAILS_SPENDING_ADJUSTMENT_PCT = 0.10

# Age at which Medicare eligibility begins; before this, a retired person
# needs marketplace/COBRA-style coverage instead.
MEDICARE_ELIGIBILITY_AGE = 65
# Flat estimated annual premium per person for pre-Medicare coverage, in
# today's dollars (inflated like other spending). A rough marketplace
# planning estimate — edit to match your own quotes.
PRE_MEDICARE_ANNUAL_PREMIUM_PER_PERSON = 12_000

# 2024 Medicare Part B + Part D base premiums (per person, per year).
MEDICARE_PART_B_BASE_ANNUAL_PREMIUM = 174.70 * 12
MEDICARE_PART_D_BASE_ANNUAL_PREMIUM = 55.50 * 12

# IRMAA (Income-Related Monthly Adjustment Amount): Medicare Part B/D
# premiums rise in tiers based on MAGI from two years prior. Each tuple is
# (MAGI upper bound for this tier, Part B monthly surcharge, Part D monthly
# surcharge), ascending, per filing status. 2024 figures — edit yearly.
IRMAA_BRACKETS = {
    "single": [
        (103_000, 0.0, 0.0),
        (129_000, 69.90, 12.90),
        (161_000, 174.70, 33.30),
        (193_000, 279.50, 53.80),
        (500_000, 384.30, 74.20),
        (float("inf"), 419.30, 81.00),
    ],
    "married_filing_jointly": [
        (206_000, 0.0, 0.0),
        (258_000, 69.90, 12.90),
        (322_000, 174.70, 33.30),
        (386_000, 279.50, 53.80),
        (750_000, 384.30, 74.20),
        (float("inf"), 419.30, 81.00),
    ],
}

# Monte Carlo defaults: each trial applies a randomized annual return shock
# (same shock across every account that year, since diversified growth
# assets broadly move with the market) drawn from a normal distribution
# centered on 0 with this standard deviation, added to each account's own
# expected return for that year.
MONTE_CARLO_DEFAULT_SIMULATIONS = 500
MONTE_CARLO_DEFAULT_RETURN_VOLATILITY = 0.15
