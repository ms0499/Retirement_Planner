"""
Phase 4: synthesizes the projection, tax-planning, guardrails, and Monte
Carlo outputs (Phases 1-3) into a single prioritized list of concrete
actions. Nothing here is a new financial model — each item is either a
closed-form calculation on top of the existing projection, or a handful of
extra ephemeral what-if re-runs of the same engine, mirroring the pattern
already used by social_security.py and whatif.py.
"""

from app.constants import (
    MONTE_CARLO_DEFAULT_RETURN_VOLATILITY,
    SOCIAL_SECURITY_MAX_CLAIM_AGE,
)
from app.models.account import Account
from app.models.assumptions import HouseholdAssumptions
from app.models.expense import ExpenseCategory
from app.models.person import Person
from app.schemas.action_plan import ActionItem, ActionPlanOut
from app.schemas.whatif import PersonOverride, WhatIfInput
from app.services.calculations import build_projection, roth_conversion_opportunities
from app.services.monte_carlo import run_monte_carlo
from app.services.social_security import adjusted_monthly_benefit
from app.services.whatif import run_what_if

# Lower number = shown first. Non-discretionary/free levers (guardrails,
# closing a contribution gap) are ranked ahead of lifestyle sacrifices
# (delaying retirement, cutting spending).
_CATEGORY_ORDER = {
    "contribution": 0,
    "guardrails": 1,
    "social_security": 2,
    "roth_conversion": 3,
    "retirement_age": 4,
    "spending": 5,
}

_RETIREMENT_DELAY_SEARCH_MAX_YEARS = 10
_SPENDING_CUT_SEARCH_STEP_PCT = 0.05
_SPENDING_CUT_SEARCH_MIN_MULTIPLIER = 0.5
_ACTION_PLAN_MONTE_CARLO_SIMULATIONS = 300
_MIN_MEANINGFUL_MONTHLY_SS_DELTA = 25.0


def build_action_plan(
    people: list[Person],
    accounts: list[Account],
    expense_categories: list[ExpenseCategory],
    assumptions: HouseholdAssumptions,
) -> ActionPlanOut:
    baseline = build_projection(people, accounts, expense_categories, assumptions)
    monte_carlo = run_monte_carlo(
        people,
        accounts,
        expense_categories,
        assumptions,
        num_simulations=_ACTION_PLAN_MONTE_CARLO_SIMULATIONS,
        return_volatility=MONTE_CARLO_DEFAULT_RETURN_VOLATILITY,
    )

    items: list[ActionItem] = []

    if baseline.depletion_shortfall:
        items += _guardrails_item(people, accounts, expense_categories, assumptions)
        items += _retirement_delay_item(people, accounts, expense_categories, assumptions)
        items += _spending_cut_item(people, accounts, expense_categories, assumptions)

    shortfall = baseline.required_nest_egg - baseline.projected_balance_at_retirement
    if shortfall > 0 and baseline.years_to_retirement > 0:
        items += _contribution_item(shortfall, baseline.years_to_retirement, assumptions)

    items += _social_security_items(people)
    items += _roth_conversion_item(people, accounts, expense_categories, assumptions)

    items.sort(key=lambda item: _CATEGORY_ORDER.get(item.category, 99))
    for idx, item in enumerate(items, start=1):
        item.priority = idx

    return ActionPlanOut(
        is_on_track=baseline.is_on_track,
        money_lasts_to_year_index=baseline.money_lasts_to_year_index,
        monte_carlo_success_rate=monte_carlo.success_rate,
        items=items,
    )


def _contribution_item(
    shortfall: float, years_to_retirement: int, assumptions: HouseholdAssumptions
) -> list[ActionItem]:
    r = float(assumptions.expected_return)
    n = years_to_retirement
    # Future value of an ordinary annuity, solved for the payment: how much
    # more would need to be contributed each year (growing at the assumed
    # return) to close the gap between the projected and required balance.
    extra_annual = shortfall / n if r == 0 else shortfall * r / ((1 + r) ** n - 1)
    return [
        ActionItem(
            priority=0,
            category="contribution",
            title=f"Increase annual contributions by about ${extra_annual:,.0f}",
            description=(
                f"Your projected balance at retirement is about ${shortfall:,.0f} short of "
                f"your number. Spreading roughly ${extra_annual:,.0f}/year in extra "
                f"contributions across your accounts over the {n} years until retirement "
                f"(growing at your assumed {r * 100:.1f}% return) would close that gap."
            ),
        )
    ]


def _guardrails_item(
    people: list[Person],
    accounts: list[Account],
    expense_categories: list[ExpenseCategory],
    assumptions: HouseholdAssumptions,
) -> list[ActionItem]:
    with_guardrails = build_projection(
        people, accounts, expense_categories, assumptions, use_guardrails=True
    )
    if with_guardrails.depletion_shortfall:
        return []
    return [
        ActionItem(
            priority=0,
            category="guardrails",
            title="Turn on dynamic spending guardrails",
            description=(
                "Letting spending flex down when the portfolio is running hot and back up "
                "when it recovers, instead of a fixed inflation-adjusted amount, is enough on "
                "its own to keep your money from running out across your full horizon. Try it "
                "in the What-if lab."
            ),
        )
    ]


def _retirement_delay_item(
    people: list[Person],
    accounts: list[Account],
    expense_categories: list[ExpenseCategory],
    assumptions: HouseholdAssumptions,
) -> list[ActionItem]:
    for delta in range(1, _RETIREMENT_DELAY_SEARCH_MAX_YEARS + 1):
        overrides = WhatIfInput(
            person_overrides=[
                PersonOverride(person_id=p.id, retirement_age=p.retirement_age + delta)
                for p in people
            ]
        )
        projection = run_what_if(people, accounts, expense_categories, assumptions, overrides)
        if not projection.depletion_shortfall:
            plural = "s" if delta != 1 else ""
            return [
                ActionItem(
                    priority=0,
                    category="retirement_age",
                    title=f"Delay retirement by {delta} year{plural}",
                    description=(
                        f"Pushing everyone's retirement age back by {delta} year{plural} — more "
                        "time contributing, less time drawing down — is enough for your money "
                        "to last your full horizon at your current spending level."
                    ),
                )
            ]
    return []


def _spending_cut_item(
    people: list[Person],
    accounts: list[Account],
    expense_categories: list[ExpenseCategory],
    assumptions: HouseholdAssumptions,
) -> list[ActionItem]:
    multiplier = 1.0 - _SPENDING_CUT_SEARCH_STEP_PCT
    while multiplier >= _SPENDING_CUT_SEARCH_MIN_MULTIPLIER:
        overrides = WhatIfInput(spending_multiplier=multiplier)
        projection = run_what_if(people, accounts, expense_categories, assumptions, overrides)
        if not projection.depletion_shortfall:
            cut_pct = round((1 - multiplier) * 100)
            return [
                ActionItem(
                    priority=0,
                    category="spending",
                    title=f"Cut planned spending by about {cut_pct}%",
                    description=(
                        f"Reducing post-retirement spending by roughly {cut_pct}% versus your "
                        "current plan would let your money last your full horizon without any "
                        "other changes."
                    ),
                )
            ]
        multiplier -= _SPENDING_CUT_SEARCH_STEP_PCT
    return []


def _social_security_items(people: list[Person]) -> list[ActionItem]:
    items = []
    for p in people:
        if p.current_age >= SOCIAL_SECURITY_MAX_CLAIM_AGE or p.social_security_claim_age >= SOCIAL_SECURITY_MAX_CLAIM_AGE:
            continue
        fra_benefit = float(p.social_security_monthly_estimate)
        if fra_benefit <= 0:
            continue
        current_benefit = adjusted_monthly_benefit(fra_benefit, p.social_security_claim_age)
        max_benefit = adjusted_monthly_benefit(fra_benefit, SOCIAL_SECURITY_MAX_CLAIM_AGE)
        delta = max_benefit - current_benefit
        if delta < _MIN_MEANINGFUL_MONTHLY_SS_DELTA:
            continue
        items.append(
            ActionItem(
                priority=0,
                category="social_security",
                title=f"Delay {p.name}'s Social Security to age {SOCIAL_SECURITY_MAX_CLAIM_AGE} for +${delta:,.0f}/mo",
                description=(
                    f"{p.name} is set to claim at {p.social_security_claim_age}, worth about "
                    f"${current_benefit:,.0f}/mo. Waiting until {SOCIAL_SECURITY_MAX_CLAIM_AGE} "
                    f"would raise that to about ${max_benefit:,.0f}/mo, guaranteed for life. See "
                    "Tax planning for the full claiming-age comparison."
                ),
            )
        )
    return items


def _roth_conversion_item(
    people: list[Person],
    accounts: list[Account],
    expense_categories: list[ExpenseCategory],
    assumptions: HouseholdAssumptions,
) -> list[ActionItem]:
    result = roth_conversion_opportunities(people, accounts, expense_categories, assumptions)
    if not result.opportunities:
        return []
    total = sum(o.suggested_conversion for o in result.opportunities)
    return [
        ActionItem(
            priority=0,
            category="roth_conversion",
            title=f"Convert about ${total:,.0f} to Roth before RMDs start",
            description=(
                f"Between {result.window_start_year_index} and {result.window_end_year_index} "
                "years from now, taxable income is low enough to convert tax-deferred balances "
                f"to Roth while staying inside the {result.target_bracket_rate * 100:.0f}% "
                "bracket — about "
                f"${total:,.0f} total across that window. See Tax planning for the year-by-year "
                "breakdown."
            ),
        )
    ]
