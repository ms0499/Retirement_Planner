"""
Phase 5: "top strategies" optimizer. Grid-searches Roth-conversion
aggressiveness (see roth_conversion_target_rate in build_projection) crossed
with the guardrails on/off toggle, and ranks each combination by after-tax
ending wealth — the plan's ending balance with tax-deferred dollars
discounted by TOP_STRATEGY_ASSUMED_FUTURE_TAX_RATE, since that money is
never fully the household's (see constants.py). Roth and taxable balances
already are after-tax, so they count at face value.

A combination that depletes the portfolio before the horizon ends is only
chosen if every combination depletes (there, the least-bad option is still
reported so the endpoint always returns something actionable) — otherwise
depleting combinations are excluded from the winner search entirely, since
a higher paper "ending wealth" from a plan that runs out of money years
earlier isn't actually better.

No new financial model: every candidate is just another build_projection
call, exactly like whatif.py and action_plan.py already do.
"""

from app.constants import (
    TOP_STRATEGY_ASSUMED_FUTURE_TAX_RATE,
    TOP_STRATEGY_CONVERSION_RATE_CANDIDATES,
)
from app.models.account import Account
from app.models.assumptions import HouseholdAssumptions
from app.models.expense import ExpenseCategory
from app.models.person import Person
from app.schemas.top_strategy import StrategyCandidate, TopStrategyOut
from app.services.calculations import build_projection

_GUARDRAILS_CANDIDATES = [False, True]


def _after_tax_ending_wealth(projection) -> float:
    ending_year = projection.timeline[-1]
    return ending_year.balance - ending_year.tax_deferred_balance * TOP_STRATEGY_ASSUMED_FUTURE_TAX_RATE


def find_top_strategy(
    people: list[Person],
    accounts: list[Account],
    expense_categories: list[ExpenseCategory],
    assumptions: HouseholdAssumptions,
) -> TopStrategyOut:
    candidates: list[StrategyCandidate] = []
    baseline: StrategyCandidate | None = None

    for target_rate in TOP_STRATEGY_CONVERSION_RATE_CANDIDATES:
        for use_guardrails in _GUARDRAILS_CANDIDATES:
            projection = build_projection(
                people,
                accounts,
                expense_categories,
                assumptions,
                use_guardrails=use_guardrails,
                roth_conversion_target_rate=target_rate,
            )
            candidate = StrategyCandidate(
                roth_conversion_target_rate=target_rate,
                use_guardrails=use_guardrails,
                depletion_shortfall=projection.depletion_shortfall,
                after_tax_ending_wealth=round(_after_tax_ending_wealth(projection), 2),
            )
            candidates.append(candidate)
            if target_rate is None and not use_guardrails:
                baseline = candidate

    assert baseline is not None  # (None, False) is always in the grid above

    survivors = [c for c in candidates if not c.depletion_shortfall]
    pool = survivors if survivors else candidates
    best = max(pool, key=lambda c: c.after_tax_ending_wealth)

    candidates.sort(key=lambda c: (c.depletion_shortfall, -c.after_tax_ending_wealth))

    return TopStrategyOut(
        assumed_future_tax_rate=TOP_STRATEGY_ASSUMED_FUTURE_TAX_RATE,
        baseline=baseline,
        best=best,
        improvement_vs_baseline=round(
            best.after_tax_ending_wealth - baseline.after_tax_ending_wealth, 2
        ),
        candidates=candidates,
    )
