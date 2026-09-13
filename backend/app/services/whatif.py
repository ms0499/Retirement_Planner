"""
Ephemeral "what-if" projections: applies temporary overrides (per-person
retirement/claiming age, expected return, inflation rate, safe withdrawal
rate, an overall spending multiplier, and an optional dynamic-spending-
guardrails toggle) without persisting anything to the database. Reuses the
same duck-typed snapshot pattern as social_security.py so the real ORM
objects loaded in the request's session are never mutated mid-request.
"""

from dataclasses import dataclass

from app.models.account import Account
from app.models.assumptions import HouseholdAssumptions
from app.models.expense import ExpenseCategory
from app.models.person import Person
from app.schemas.projection import ProjectionOut
from app.schemas.whatif import WhatIfInput
from app.services.calculations import build_projection


@dataclass
class _PersonSnapshot:
    id: int
    current_age: int
    retirement_age: int
    life_expectancy: int
    social_security_monthly_estimate: float
    social_security_claim_age: int
    pension_monthly: float


@dataclass
class _AssumptionsSnapshot:
    inflation_rate: float
    expected_return: float
    safe_withdrawal_rate: float
    lifestyle_preset: object
    filing_status: object


def run_what_if(
    people: list[Person],
    accounts: list[Account],
    expense_categories: list[ExpenseCategory],
    assumptions: HouseholdAssumptions,
    overrides: WhatIfInput,
) -> ProjectionOut:
    override_by_person = {o.person_id: o for o in overrides.person_overrides}

    snapshots = []
    for p in people:
        o = override_by_person.get(p.id)
        snapshots.append(
            _PersonSnapshot(
                id=p.id,
                current_age=p.current_age,
                retirement_age=(
                    o.retirement_age if o and o.retirement_age is not None else p.retirement_age
                ),
                life_expectancy=p.life_expectancy,
                social_security_monthly_estimate=float(p.social_security_monthly_estimate),
                social_security_claim_age=(
                    o.social_security_claim_age
                    if o and o.social_security_claim_age is not None
                    else p.social_security_claim_age
                ),
                pension_monthly=float(p.pension_monthly),
            )
        )

    assumptions_snapshot = _AssumptionsSnapshot(
        inflation_rate=(
            overrides.inflation_rate
            if overrides.inflation_rate is not None
            else float(assumptions.inflation_rate)
        ),
        expected_return=(
            overrides.expected_return
            if overrides.expected_return is not None
            else float(assumptions.expected_return)
        ),
        safe_withdrawal_rate=(
            overrides.safe_withdrawal_rate
            if overrides.safe_withdrawal_rate is not None
            else float(assumptions.safe_withdrawal_rate)
        ),
        lifestyle_preset=assumptions.lifestyle_preset,
        filing_status=assumptions.filing_status,
    )

    return build_projection(
        snapshots,
        accounts,
        expense_categories,
        assumptions_snapshot,
        spending_multiplier=overrides.spending_multiplier,
        use_guardrails=overrides.use_guardrails,
    )
