"""
Monte Carlo simulation: instead of one deterministic market-return path,
runs many trials with randomized annual return shocks and reports the
fraction of trials that never deplete the portfolio, plus p10/p50/p90
balance bands for charting.

Simplifying assumption: each trial draws one return shock per year from a
normal distribution (mean 0, stdev = return_volatility) and applies it
identically to every account that year — diversified growth accounts are
assumed to broadly move together with the market, rather than modeling
per-asset-class correlations. Applied on top of each account's own
expected return (or override), so relative return differences between
accounts are preserved.
"""

import random

from app.constants import MONTE_CARLO_DEFAULT_RETURN_VOLATILITY, MONTE_CARLO_DEFAULT_SIMULATIONS
from app.models.account import Account
from app.models.assumptions import HouseholdAssumptions
from app.models.expense import ExpenseCategory
from app.models.person import Person
from app.schemas.projection import MonteCarloOut, MonteCarloYearBand
from app.services.calculations import build_projection


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, round(pct * (len(sorted_values) - 1))))
    return sorted_values[idx]


def run_monte_carlo(
    people: list[Person],
    accounts: list[Account],
    expense_categories: list[ExpenseCategory],
    assumptions: HouseholdAssumptions,
    num_simulations: int = MONTE_CARLO_DEFAULT_SIMULATIONS,
    return_volatility: float = MONTE_CARLO_DEFAULT_RETURN_VOLATILITY,
) -> MonteCarloOut:
    baseline = build_projection(people, accounts, expense_categories, assumptions)
    horizon_years = len(baseline.timeline) - 1

    successes = 0
    depletion_years: list[int] = []
    balances_by_year: list[list[float]] = [[] for _ in range(horizon_years + 1)]

    for _ in range(num_simulations):
        shocks = [random.gauss(0.0, return_volatility) for _ in range(horizon_years + 1)]
        trial = build_projection(
            people, accounts, expense_categories, assumptions, return_shocks=shocks
        )
        if trial.money_lasts_to_year_index is None:
            successes += 1
        else:
            depletion_years.append(trial.money_lasts_to_year_index)
        for year in trial.timeline:
            balances_by_year[year.year_index].append(year.balance)

    bands: list[MonteCarloYearBand] = []
    for year_index, balances in enumerate(balances_by_year):
        balances.sort()
        bands.append(
            MonteCarloYearBand(
                year_index=year_index,
                p10=round(_percentile(balances, 0.10), 2),
                p50=round(_percentile(balances, 0.50), 2),
                p90=round(_percentile(balances, 0.90), 2),
            )
        )

    depletion_years.sort()
    median_depletion_year_index = (
        depletion_years[len(depletion_years) // 2]
        if len(depletion_years) > num_simulations / 2
        else None
    )

    return MonteCarloOut(
        num_simulations=num_simulations,
        return_volatility=return_volatility,
        success_rate=round(successes / num_simulations, 4),
        median_depletion_year_index=median_depletion_year_index,
        years_to_retirement=baseline.years_to_retirement,
        bands=bands,
    )
