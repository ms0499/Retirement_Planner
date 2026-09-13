"""
Federal ordinary-income tax helpers used by the projection engine.

Simplifying assumptions (documented once, here, rather than at each call
site):
- Only federal tax is modeled — no state income tax (varies too much to
  bake in a sane default; a per-household override could be added later).
- Taxable-account (brokerage/cash) withdrawals are treated as already-taxed
  principal — no capital-gains tax is modeled. A real brokerage withdrawal
  may carry some gains, but tracking cost basis is a Phase 3-sized feature.
- Social Security taxability uses the standard simplified IRS worksheet,
  with "other income" approximated as pension + RMDs for the year (see
  calculations.py) rather than the fully circular definition that would
  also include discretionary withdrawals — a minor, conservative
  simplification that keeps the withdrawal solve tractable.
"""

from app.constants import (
    FEDERAL_TAX_BRACKETS,
    RMD_START_AGE,
    RMD_UNIFORM_LIFETIME_TABLE,
    SOCIAL_SECURITY_TAXABILITY_THRESHOLDS,
    STANDARD_DEDUCTION,
)


def marginal_tax(taxable_income: float, filing_status: str) -> float:
    """Progressive federal tax on already-deduction-adjusted taxable income."""
    if taxable_income <= 0:
        return 0.0
    brackets = FEDERAL_TAX_BRACKETS[filing_status]
    tax = 0.0
    for i, (lower, rate) in enumerate(brackets):
        upper = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
        if taxable_income <= lower:
            break
        tax += (min(taxable_income, upper) - lower) * rate
    return tax


def ordinary_income_tax(gross_ordinary_income: float, filing_status: str) -> float:
    """Federal tax on gross ordinary income, after the standard deduction."""
    deduction = STANDARD_DEDUCTION[filing_status]
    taxable = max(0.0, gross_ordinary_income - deduction)
    return marginal_tax(taxable, filing_status)


def taxable_social_security(
    ss_annual: float, other_ordinary_income: float, filing_status: str
) -> float:
    """How much of this year's Social Security benefit is taxable (simplified worksheet)."""
    if ss_annual <= 0:
        return 0.0
    lower, upper = SOCIAL_SECURITY_TAXABILITY_THRESHOLDS[filing_status]
    provisional_income = other_ordinary_income + 0.5 * ss_annual
    if provisional_income <= lower:
        return 0.0
    if provisional_income <= upper:
        return min(0.5 * ss_annual, 0.5 * (provisional_income - lower))
    tier1 = min(0.5 * ss_annual, 0.5 * (upper - lower))
    tier2 = 0.85 * (provisional_income - upper)
    return min(0.85 * ss_annual, tier1 + tier2)


def rmd_divisor(age: int) -> float | None:
    if age in RMD_UNIFORM_LIFETIME_TABLE:
        return RMD_UNIFORM_LIFETIME_TABLE[age]
    if age < min(RMD_UNIFORM_LIFETIME_TABLE):
        return None
    return RMD_UNIFORM_LIFETIME_TABLE[max(RMD_UNIFORM_LIFETIME_TABLE)]


def required_minimum_distribution(age: int, prior_year_end_balance: float) -> float:
    if age < RMD_START_AGE or prior_year_end_balance <= 0:
        return 0.0
    divisor = rmd_divisor(age)
    if not divisor:
        return 0.0
    return prior_year_end_balance / divisor


def solve_tax_deferred_withdrawal_for_net(
    remaining_need: float,
    baseline_ordinary_income: float,
    filing_status: str,
    available_balance: float,
) -> float:
    """
    How much extra must be withdrawn from a tax-deferred account (on top of
    baseline_ordinary_income, which is already taxed) so the after-tax
    proceeds cover remaining_need? Solved by bisection since tax owed is a
    monotonic but non-linear (bracket-crossing) function of the withdrawal.
    Capped at available_balance — the caller sees a shortfall if even that
    isn't enough.
    """
    if remaining_need <= 0 or available_balance <= 0:
        return 0.0

    base_tax = ordinary_income_tax(baseline_ordinary_income, filing_status)

    def net_proceeds(withdrawal: float) -> float:
        tax = ordinary_income_tax(baseline_ordinary_income + withdrawal, filing_status)
        return withdrawal - (tax - base_tax)

    if net_proceeds(available_balance) <= remaining_need:
        return available_balance

    lo, hi = 0.0, available_balance
    for _ in range(50):
        mid = (lo + hi) / 2
        if net_proceeds(mid) < remaining_need:
            lo = mid
        else:
            hi = mid
    return hi
