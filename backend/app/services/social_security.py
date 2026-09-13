"""
Social Security claiming-age mechanics and the 62 / FRA / 70 comparison.

No birthdate is collected (only current_age), so — like most simplified
planners — everyone's Full Retirement Age is assumed to be 67 (correct for
anyone born 1960 or later). `social_security_monthly_estimate` on Person is
treated as the FRA benefit estimate, since that's what SSA statements show.
"""

from dataclasses import dataclass

from app.constants import (
    SOCIAL_SECURITY_DELAYED_CREDIT_RATE_PER_MONTH,
    SOCIAL_SECURITY_EARLY_REDUCTION_RATE_ADDITIONAL_MONTHS,
    SOCIAL_SECURITY_EARLY_REDUCTION_RATE_FIRST_36_MONTHS,
    SOCIAL_SECURITY_FULL_RETIREMENT_AGE,
    SOCIAL_SECURITY_MAX_CLAIM_AGE,
    SOCIAL_SECURITY_MIN_CLAIM_AGE,
)
from app.models.account import Account
from app.models.assumptions import HouseholdAssumptions
from app.models.expense import ExpenseCategory
from app.models.person import Person
from app.schemas.projection import SocialSecurityClaimingOption, SocialSecurityComparisonOut
from app.services.calculations import build_projection


def adjusted_monthly_benefit(fra_monthly_benefit: float, claim_age: int) -> float:
    """Adjust an FRA-estimate benefit for claiming earlier or later than 67."""
    claim_age = max(SOCIAL_SECURITY_MIN_CLAIM_AGE, min(SOCIAL_SECURITY_MAX_CLAIM_AGE, claim_age))
    months_diff = (claim_age - SOCIAL_SECURITY_FULL_RETIREMENT_AGE) * 12
    if months_diff == 0:
        return fra_monthly_benefit
    if months_diff < 0:
        months_early = -months_diff
        first_36 = min(months_early, 36)
        remainder = max(0, months_early - 36)
        reduction = (
            first_36 * SOCIAL_SECURITY_EARLY_REDUCTION_RATE_FIRST_36_MONTHS
            + remainder * SOCIAL_SECURITY_EARLY_REDUCTION_RATE_ADDITIONAL_MONTHS
        )
        return fra_monthly_benefit * (1 - reduction)
    months_late = months_diff
    increase = months_late * SOCIAL_SECURITY_DELAYED_CREDIT_RATE_PER_MONTH
    return fra_monthly_benefit * (1 + increase)


CLAIMING_AGE_OPTIONS = [SOCIAL_SECURITY_MIN_CLAIM_AGE, SOCIAL_SECURITY_FULL_RETIREMENT_AGE, SOCIAL_SECURITY_MAX_CLAIM_AGE]


@dataclass
class _PersonSnapshot:
    """Duck-typed stand-in for Person so we can vary claim age/benefit
    without mutating the real ORM objects loaded in the request's session."""

    id: int
    current_age: int
    retirement_age: int
    life_expectancy: int
    social_security_monthly_estimate: float
    social_security_claim_age: int
    pension_monthly: float


def _snapshot(p: Person, claim_age: int | None = None, benefit: float | None = None) -> _PersonSnapshot:
    return _PersonSnapshot(
        id=p.id,
        current_age=p.current_age,
        retirement_age=p.retirement_age,
        life_expectancy=p.life_expectancy,
        social_security_monthly_estimate=(
            benefit if benefit is not None else float(p.social_security_monthly_estimate)
        ),
        social_security_claim_age=(
            claim_age if claim_age is not None else p.social_security_claim_age
        ),
        pension_monthly=float(p.pension_monthly),
    )


def compare_claiming_ages(
    people: list[Person],
    accounts: list[Account],
    expense_categories: list[ExpenseCategory],
    assumptions: HouseholdAssumptions,
    person_id: int,
) -> SocialSecurityComparisonOut:
    """
    Re-runs the full projection three times for one person's claiming age
    (62 / FRA / 70), holding everyone else's assumptions fixed, so the
    household can see the tradeoff between claiming early vs. delaying.
    `social_security_monthly_estimate` on file is treated as the FRA benefit.
    """
    target = next((p for p in people if p.id == person_id), None)
    if target is None:
        raise ValueError(f"Person {person_id} not found in this household")

    fra_benefit = float(target.social_security_monthly_estimate)

    options = []
    for claim_age in CLAIMING_AGE_OPTIONS:
        adjusted = adjusted_monthly_benefit(fra_benefit, claim_age)
        snapshots = [
            _snapshot(p, claim_age=claim_age, benefit=adjusted)
            if p.id == person_id
            else _snapshot(p)
            for p in people
        ]
        projection = build_projection(snapshots, accounts, expense_categories, assumptions)
        options.append(
            SocialSecurityClaimingOption(
                claim_age=claim_age,
                adjusted_monthly_benefit=round(adjusted, 2),
                projection=projection,
            )
        )

    return SocialSecurityComparisonOut(
        person_id=target.id,
        person_name=target.name,
        fra_monthly_benefit=round(fra_benefit, 2),
        options=options,
    )
