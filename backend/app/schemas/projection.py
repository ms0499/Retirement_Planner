from pydantic import BaseModel


class YearProjection(BaseModel):
    year_index: int
    phase: str  # "accumulation" | "decumulation"
    balance: float
    guaranteed_income: float
    spending_need: float
    tax_paid: float
    rmd_amount: float
    taxable_ordinary_income: float
    tax_deferred_balance: float
    healthcare_cost: float
    guardrail_action: str  # "none" | "cut" | "raise"


class ProjectionOut(BaseModel):
    required_nest_egg: float
    projected_balance_at_retirement: float
    years_to_retirement: int
    is_on_track: bool
    money_lasts_to_year_index: int | None  # None means it never depletes within the horizon
    depletion_shortfall: bool
    total_lifetime_tax_paid: float
    timeline: list[YearProjection]


class SocialSecurityClaimingOption(BaseModel):
    claim_age: int
    adjusted_monthly_benefit: float
    projection: ProjectionOut


class SocialSecurityComparisonOut(BaseModel):
    person_id: int
    person_name: str
    fra_monthly_benefit: float
    options: list[SocialSecurityClaimingOption]


class RothConversionOpportunity(BaseModel):
    year_index: int
    taxable_ordinary_income: float
    target_bracket_rate: float
    bracket_ceiling: float
    room_to_fill_bracket: float
    tax_deferred_balance: float
    suggested_conversion: float


class RothConversionOpportunitiesOut(BaseModel):
    window_start_year_index: int
    window_end_year_index: int
    target_bracket_rate: float
    opportunities: list[RothConversionOpportunity]


class MonteCarloYearBand(BaseModel):
    year_index: int
    p10: float
    p50: float
    p90: float


class MonteCarloOut(BaseModel):
    num_simulations: int
    return_volatility: float
    success_rate: float  # fraction of trials that never deplete the portfolio
    median_depletion_year_index: int | None  # None if fewer than half of trials deplete
    years_to_retirement: int
    bands: list[MonteCarloYearBand]
