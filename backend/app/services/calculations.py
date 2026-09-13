"""
Core retirement math: the "your number" calculation and the year-by-year
accumulation/decumulation projection, tax-, withdrawal-order-, and
healthcare-aware, with optional Monte Carlo return shocks and dynamic
spending guardrails (Phase 3).

Simplifying assumptions (Phase 1 & 2, extended in Phase 3):
- The household is treated as retiring together once the FIRST person
  reaches their target retirement age (years_to_retirement = min across
  people). This is the point where contributions stop and withdrawals
  begin. Modeling staggered individual retirement dates is deferred.
- The projection horizon runs until the LAST person's life expectancy
  (years_from_now = max across people), so the plan must fund the
  household until the longer-lived person's expected age.
- Each account grows at its own expected_return_override if set, else the
  household's expected_return, plus that year's return shock if the caller
  supplied one (see `return_shocks`, used by the Monte Carlo service).
- In decumulation, withdrawals are tax-aware and follow the conventional
  ordering: (1) that year's Required Minimum Distributions are forced out
  of each person's own tax-deferred accounts once they reach RMD_START_AGE;
  any RMD proceeds beyond that year's spending need are reinvested back
  into the household's taxable bucket; (2) remaining spending need is met
  from taxable accounts first (assumed already-taxed, no capital-gains
  modeling); (3) then additional tax-deferred withdrawals, grossed up so
  the after-tax proceeds cover the gap; (4) finally Roth accounts
  (tax-free). See app/services/tax.py for the tax math itself.
- A tax-deferred or Roth account with no assigned person is split evenly
  across the household's people, since those account types must legally
  have an individual owner. Taxable accounts with no assigned person stay
  in a shared household-level taxable bucket.
- Contribution and lifestyle spending amounts grow with the household's
  inflation rate each year, in nominal dollars.
- Healthcare premiums (pre-Medicare coverage or Medicare Part B/D + IRMAA,
  see app/services/healthcare.py) are added on top of lifestyle spending
  each retirement year, and are NOT subject to spending-guardrail cuts —
  they're modeled as non-discretionary.
- Dynamic spending guardrails (Guyton-Klinger style), when enabled, compare
  each year's lifestyle withdrawal rate against the rate set at retirement
  and nudge lifestyle spending down/up by a fixed step when it drifts too
  far — see GUARDRAILS_* constants.
"""

from dataclasses import dataclass

from app.constants import (
    GUARDRAILS_LOWER_TRIGGER_PCT,
    GUARDRAILS_SPENDING_ADJUSTMENT_PCT,
    GUARDRAILS_UPPER_TRIGGER_PCT,
    LIFESTYLE_PRESET_ANNUAL_SPEND,
    ROTH_CONVERSION_TARGET_BRACKET_RATE,
    STANDARD_DEDUCTION,
)
from app.constants import FEDERAL_TAX_BRACKETS, RMD_START_AGE
from app.models.account import Account, AccountType
from app.models.assumptions import HouseholdAssumptions, LifestylePreset
from app.models.expense import ExpenseCategory
from app.models.person import Person
from app.schemas.projection import (
    ProjectionOut,
    RothConversionOpportunitiesOut,
    RothConversionOpportunity,
    YearProjection,
)
from app.services.healthcare import annual_healthcare_cost
from app.services.tax import (
    ordinary_income_tax,
    required_minimum_distribution,
    solve_tax_deferred_withdrawal_for_net,
    taxable_social_security,
)

TAX_BUCKET_BY_ACCOUNT_TYPE = {
    AccountType.TRADITIONAL_401K: "tax_deferred",
    AccountType.TRADITIONAL_IRA: "tax_deferred",
    AccountType.ROTH_401K: "roth",
    AccountType.ROTH_IRA: "roth",
    AccountType.HSA: "roth",  # tax-free when used for qualified medical expenses — simplification
    AccountType.BROKERAGE: "taxable",
    AccountType.CASH: "taxable",
}


@dataclass
class _AccountState:
    person_id: int | None
    bucket: str
    balance: float
    rate: float
    annual_contribution: float
    annual_employer_match: float


def _build_account_states(
    people: list[Person], accounts: list[Account], default_rate: float
) -> list[_AccountState]:
    states: list[_AccountState] = []
    n_people = len(people)
    for a in accounts:
        bucket = TAX_BUCKET_BY_ACCOUNT_TYPE[a.account_type]
        rate = float(a.expected_return_override) if a.expected_return_override is not None else default_rate
        if a.person_id is not None or bucket == "taxable":
            states.append(
                _AccountState(
                    person_id=a.person_id,
                    bucket=bucket,
                    balance=float(a.balance),
                    rate=rate,
                    annual_contribution=float(a.annual_contribution),
                    annual_employer_match=float(a.annual_employer_match),
                )
            )
        else:
            # Tax-advantaged account with no owner on file — must legally
            # belong to one person, so split evenly across the household.
            for p in people:
                states.append(
                    _AccountState(
                        person_id=p.id,
                        bucket=bucket,
                        balance=float(a.balance) / n_people,
                        rate=rate,
                        annual_contribution=float(a.annual_contribution) / n_people,
                        annual_employer_match=float(a.annual_employer_match) / n_people,
                    )
                )
    if not any(s.bucket == "taxable" for s in states):
        states.append(_AccountState(None, "taxable", 0.0, default_rate, 0.0, 0.0))
    return states


def _withdraw_from_bucket(states: list[_AccountState], bucket: str, amount: float) -> float:
    remaining = amount
    for s in states:
        if remaining <= 0:
            break
        if s.bucket == bucket and s.balance > 0:
            take = min(s.balance, remaining)
            s.balance -= take
            remaining -= take
    return amount - remaining


def _reinvest_surplus(states: list[_AccountState], surplus: float) -> None:
    taxable_states = [s for s in states if s.bucket == "taxable"]
    total = sum(s.balance for s in taxable_states)
    if total > 0:
        for s in taxable_states:
            s.balance += surplus * (s.balance / total)
    else:
        taxable_states[0].balance += surplus


def _guaranteed_income_detail(people: list[Person], year_index: int) -> tuple[float, float, float]:
    ss_cash = 0.0
    pension_cash = 0.0
    for p in people:
        age_at_t = p.current_age + year_index
        if age_at_t >= p.social_security_claim_age:
            ss_cash += float(p.social_security_monthly_estimate) * 12
        if age_at_t >= p.retirement_age:
            pension_cash += float(p.pension_monthly) * 12
    return ss_cash + pension_cash, ss_cash, pension_cash


def _guaranteed_income_at(people: list[Person], year_index: int) -> float:
    total, _, _ = _guaranteed_income_detail(people, year_index)
    return total


def _post_retirement_annual_spending(
    expense_categories: list[ExpenseCategory], lifestyle_preset: LifestylePreset
) -> float:
    total = sum(float(e.post_retirement_annual) for e in expense_categories)
    if total > 0:
        return total
    return LIFESTYLE_PRESET_ANNUAL_SPEND.get(
        lifestyle_preset.value, LIFESTYLE_PRESET_ANNUAL_SPEND["comfortable"]
    )


def build_projection(
    people: list[Person],
    accounts: list[Account],
    expense_categories: list[ExpenseCategory],
    assumptions: HouseholdAssumptions,
    return_shocks: list[float] | None = None,
    spending_multiplier: float = 1.0,
    use_guardrails: bool = False,
) -> ProjectionOut:
    if not people:
        raise ValueError("At least one person is required to build a projection")

    years_to_retirement = max(0, min(p.retirement_age - p.current_age for p in people))
    horizon_years = max(p.life_expectancy - p.current_age for p in people)
    horizon_years = max(horizon_years, years_to_retirement)

    expected_return = float(assumptions.expected_return)
    inflation_rate = float(assumptions.inflation_rate)
    safe_withdrawal_rate = float(assumptions.safe_withdrawal_rate)
    filing_status = assumptions.filing_status.value

    account_states = _build_account_states(people, accounts, expected_return)

    starting_balance = sum(s.balance for s in account_states)
    post_retirement_annual_spending = (
        _post_retirement_annual_spending(expense_categories, assumptions.lifestyle_preset)
        * spending_multiplier
    )

    guaranteed_income_at_retirement = _guaranteed_income_at(people, years_to_retirement)
    spending_gap_at_retirement = max(
        0.0, post_retirement_annual_spending - guaranteed_income_at_retirement
    )
    required_nest_egg = (
        spending_gap_at_retirement / safe_withdrawal_rate if safe_withdrawal_rate > 0 else 0.0
    )

    timeline: list[YearProjection] = []
    projected_balance_at_retirement = starting_balance
    money_lasts_to_year_index: int | None = None
    depleted = False
    total_lifetime_tax_paid = 0.0
    initial_withdrawal_rate: float | None = None
    current_spending_multiplier = 1.0

    for t in range(0, horizon_years + 1):
        shock = return_shocks[t] if return_shocks and t < len(return_shocks) else 0.0

        if t < years_to_retirement:
            phase = "accumulation"
            for s in account_states:
                contribution = (s.annual_contribution + s.annual_employer_match) * (
                    (1 + inflation_rate) ** t
                )
                s.balance = s.balance * (1 + s.rate + shock) + contribution
            guaranteed_income = 0.0
            spending_need = 0.0
            healthcare_cost = 0.0
            tax_paid = 0.0
            rmd_amount_total = 0.0
            taxable_ordinary_income = 0.0
            guardrail_action = "none"
            balance = sum(s.balance for s in account_states)
        else:
            phase = "decumulation"
            prior_by_person_tax_deferred: dict[int, float] = {}
            for s in account_states:
                if s.bucket == "tax_deferred" and s.person_id is not None:
                    prior_by_person_tax_deferred[s.person_id] = (
                        prior_by_person_tax_deferred.get(s.person_id, 0.0) + s.balance
                    )

            if t == years_to_retirement:
                projected_balance_at_retirement = sum(s.balance for s in account_states)

            for s in account_states:
                s.balance *= 1 + s.rate + shock

            guaranteed_income, ss_cash, pension_cash = _guaranteed_income_detail(people, t)
            balance_after_growth = sum(s.balance for s in account_states)
            inflated_base_spending = post_retirement_annual_spending * ((1 + inflation_rate) ** t)

            if t == years_to_retirement:
                initial_withdrawal_rate = post_retirement_annual_spending / max(
                    balance_after_growth, 1.0
                )

            guardrail_action = "none"
            if use_guardrails and initial_withdrawal_rate is not None:
                current_rate = (inflated_base_spending * current_spending_multiplier) / max(
                    balance_after_growth, 1.0
                )
                if current_rate > initial_withdrawal_rate * (1 + GUARDRAILS_UPPER_TRIGGER_PCT):
                    current_spending_multiplier *= 1 - GUARDRAILS_SPENDING_ADJUSTMENT_PCT
                    guardrail_action = "cut"
                elif current_rate < initial_withdrawal_rate * (1 - GUARDRAILS_LOWER_TRIGGER_PCT):
                    current_spending_multiplier *= 1 + GUARDRAILS_SPENDING_ADJUSTMENT_PCT
                    guardrail_action = "raise"

            spending_need = inflated_base_spending * current_spending_multiplier

            ages_this_year = [p.current_age + t for p in people]
            magi_for_irmaa = timeline[t - 2].taxable_ordinary_income if t >= 2 else 0.0
            healthcare_cost = annual_healthcare_cost(
                ages_this_year, magi_for_irmaa, filing_status
            ) * ((1 + inflation_rate) ** t)

            total_need = spending_need + healthcare_cost

            rmd_amount_total = 0.0
            for p in people:
                age_at_t = p.current_age + t
                prior_balance = prior_by_person_tax_deferred.get(p.id, 0.0)
                rmd = required_minimum_distribution(age_at_t, prior_balance)
                if rmd <= 0:
                    continue
                remaining_rmd = rmd
                for s in account_states:
                    if remaining_rmd <= 0:
                        break
                    if s.person_id == p.id and s.bucket == "tax_deferred" and s.balance > 0:
                        take = min(s.balance, remaining_rmd)
                        s.balance -= take
                        remaining_rmd -= take
                rmd_amount_total += rmd - remaining_rmd

            other_ordinary_income = pension_cash + rmd_amount_total
            ss_taxable = taxable_social_security(ss_cash, other_ordinary_income, filing_status)
            baseline_ordinary_income = other_ordinary_income + ss_taxable
            tax_on_baseline = ordinary_income_tax(baseline_ordinary_income, filing_status)

            net_cash_available = guaranteed_income + rmd_amount_total - tax_on_baseline
            remaining_need = max(0.0, total_need - net_cash_available)
            surplus = max(0.0, net_cash_available - total_need)
            if surplus > 0:
                _reinvest_surplus(account_states, surplus)

            extra_tax_deferred_withdrawal = 0.0
            if remaining_need > 0.01:
                taxable_available = sum(s.balance for s in account_states if s.bucket == "taxable")
                taken = _withdraw_from_bucket(
                    account_states, "taxable", min(remaining_need, taxable_available)
                )
                remaining_need -= taken

            if remaining_need > 0.01:
                tax_deferred_available = sum(
                    s.balance for s in account_states if s.bucket == "tax_deferred"
                )
                extra_tax_deferred_withdrawal = solve_tax_deferred_withdrawal_for_net(
                    remaining_need, baseline_ordinary_income, filing_status, tax_deferred_available
                )
                _withdraw_from_bucket(account_states, "tax_deferred", extra_tax_deferred_withdrawal)
                net_from_extra = extra_tax_deferred_withdrawal - (
                    ordinary_income_tax(
                        baseline_ordinary_income + extra_tax_deferred_withdrawal, filing_status
                    )
                    - tax_on_baseline
                )
                remaining_need -= max(0.0, net_from_extra)

            taxable_ordinary_income = baseline_ordinary_income + extra_tax_deferred_withdrawal
            tax_paid = ordinary_income_tax(taxable_ordinary_income, filing_status)

            if remaining_need > 0.01:
                roth_available = sum(s.balance for s in account_states if s.bucket == "roth")
                taken = _withdraw_from_bucket(
                    account_states, "roth", min(remaining_need, roth_available)
                )
                remaining_need -= taken

            balance = sum(s.balance for s in account_states)
            if remaining_need > 0.01 and not depleted:
                money_lasts_to_year_index = t
                depleted = True
            if depleted:
                for s in account_states:
                    s.balance = 0.0
                balance = 0.0

            total_lifetime_tax_paid += tax_paid

        timeline.append(
            YearProjection(
                year_index=t,
                phase=phase,
                balance=round(balance, 2),
                guaranteed_income=round(guaranteed_income, 2),
                spending_need=round(spending_need, 2),
                tax_paid=round(tax_paid, 2),
                rmd_amount=round(rmd_amount_total, 2),
                taxable_ordinary_income=round(taxable_ordinary_income, 2),
                tax_deferred_balance=round(
                    sum(s.balance for s in account_states if s.bucket == "tax_deferred"), 2
                ),
                healthcare_cost=round(healthcare_cost, 2),
                guardrail_action=guardrail_action,
            )
        )

    if years_to_retirement == 0:
        projected_balance_at_retirement = starting_balance

    is_on_track = projected_balance_at_retirement >= required_nest_egg
    depletion_shortfall = money_lasts_to_year_index is not None

    return ProjectionOut(
        required_nest_egg=round(required_nest_egg, 2),
        projected_balance_at_retirement=round(projected_balance_at_retirement, 2),
        years_to_retirement=years_to_retirement,
        is_on_track=is_on_track,
        money_lasts_to_year_index=money_lasts_to_year_index,
        depletion_shortfall=depletion_shortfall,
        total_lifetime_tax_paid=round(total_lifetime_tax_paid, 2),
        timeline=timeline,
    )


def _bracket_ceiling(target_rate: float, filing_status: str) -> float:
    """Top of the taxable-income band whose marginal rate is target_rate."""
    brackets = FEDERAL_TAX_BRACKETS[filing_status]
    for i, (_, rate) in enumerate(brackets):
        if rate == target_rate:
            return brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
    raise ValueError(f"No bracket with rate {target_rate} for {filing_status}")


def roth_conversion_opportunities(
    people: list[Person],
    accounts: list[Account],
    expense_categories: list[ExpenseCategory],
    assumptions: HouseholdAssumptions,
) -> RothConversionOpportunitiesOut:
    """
    Suggests, for each year between retirement and the first RMD, how much
    could be converted from tax-deferred to Roth without pushing that
    year's taxable ordinary income past the target bracket ceiling —
    "filling up" a cheaper bracket before RMDs force larger income later.
    Reuses a single build_projection run rather than re-simulating.
    """
    projection = build_projection(people, accounts, expense_categories, assumptions)
    filing_status = assumptions.filing_status.value
    ceiling = _bracket_ceiling(ROTH_CONVERSION_TARGET_BRACKET_RATE, filing_status)
    deduction = STANDARD_DEDUCTION[filing_status]

    first_rmd_year_index = min(max(0, RMD_START_AGE - p.current_age) for p in people)
    window_start = projection.years_to_retirement
    window_end = max(window_start, first_rmd_year_index)

    opportunities: list[RothConversionOpportunity] = []
    for year in projection.timeline:
        if year.year_index < window_start or year.year_index >= window_end:
            continue
        if year.tax_deferred_balance <= 0:
            continue
        taxable_income = max(0.0, year.taxable_ordinary_income - deduction)
        room = max(0.0, ceiling - taxable_income)
        suggested = min(room, year.tax_deferred_balance)
        if suggested <= 0:
            continue
        opportunities.append(
            RothConversionOpportunity(
                year_index=year.year_index,
                taxable_ordinary_income=year.taxable_ordinary_income,
                target_bracket_rate=ROTH_CONVERSION_TARGET_BRACKET_RATE,
                bracket_ceiling=ceiling,
                room_to_fill_bracket=round(room, 2),
                tax_deferred_balance=year.tax_deferred_balance,
                suggested_conversion=round(suggested, 2),
            )
        )

    return RothConversionOpportunitiesOut(
        window_start_year_index=window_start,
        window_end_year_index=window_end,
        target_bracket_rate=ROTH_CONVERSION_TARGET_BRACKET_RATE,
        opportunities=opportunities,
    )
