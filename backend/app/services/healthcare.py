"""
Healthcare cost modeling: the pre-Medicare coverage gap and Medicare Part
B/D premiums with IRMAA income-related surcharges.

Simplifying assumptions:
- A retired person under 65 pays a flat estimated annual premium for
  marketplace/COBRA-style coverage (PRE_MEDICARE_ANNUAL_PREMIUM_PER_PERSON),
  inflated like other spending by the caller.
- At 65+, Medicare Part B + Part D base premiums apply per person, plus an
  IRMAA surcharge if income is high enough. Real IRMAA is based on MAGI from
  two years prior; the caller passes in exactly that (the projection's own
  taxable ordinary income from two years back). Since this app doesn't
  model pre-retirement wages, that lookback is naturally $0 for anyone
  still in accumulation or in their first two years of retirement — a
  conservative simplification, not a special case.
- All figures are 2024 dollars — see IRMAA_BRACKETS in constants.py.
"""

from app.constants import (
    IRMAA_BRACKETS,
    MEDICARE_ELIGIBILITY_AGE,
    MEDICARE_PART_B_BASE_ANNUAL_PREMIUM,
    MEDICARE_PART_D_BASE_ANNUAL_PREMIUM,
    PRE_MEDICARE_ANNUAL_PREMIUM_PER_PERSON,
)


def irmaa_annual_surcharge(magi: float, filing_status: str) -> float:
    """Extra Part B + Part D premium per year for one Medicare-enrolled
    person, based on household MAGI from two years prior."""
    for upper, part_b_monthly, part_d_monthly in IRMAA_BRACKETS[filing_status]:
        if magi <= upper:
            return (part_b_monthly + part_d_monthly) * 12
    return 0.0


def annual_healthcare_cost(ages_this_year: list[int], magi_for_irmaa: float, filing_status: str) -> float:
    """Total household healthcare premiums for one year, in that year's
    dollars (the caller applies its own inflation factor on top)."""
    cost = 0.0
    for age in ages_this_year:
        if age < MEDICARE_ELIGIBILITY_AGE:
            cost += PRE_MEDICARE_ANNUAL_PREMIUM_PER_PERSON
        else:
            cost += MEDICARE_PART_B_BASE_ANNUAL_PREMIUM + MEDICARE_PART_D_BASE_ANNUAL_PREMIUM
            cost += irmaa_annual_surcharge(magi_for_irmaa, filing_status)
    return cost
