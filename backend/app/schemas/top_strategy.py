from pydantic import BaseModel


class StrategyCandidate(BaseModel):
    roth_conversion_target_rate: float | None
    use_guardrails: bool
    depletion_shortfall: bool
    after_tax_ending_wealth: float


class TopStrategyOut(BaseModel):
    assumed_future_tax_rate: float
    baseline: StrategyCandidate
    best: StrategyCandidate
    improvement_vs_baseline: float
    candidates: list[StrategyCandidate]
