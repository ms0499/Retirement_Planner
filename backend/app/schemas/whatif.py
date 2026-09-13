from pydantic import BaseModel


class PersonOverride(BaseModel):
    person_id: int
    retirement_age: int | None = None
    social_security_claim_age: int | None = None


class WhatIfInput(BaseModel):
    person_overrides: list[PersonOverride] = []
    expected_return: float | None = None
    inflation_rate: float | None = None
    safe_withdrawal_rate: float | None = None
    spending_multiplier: float = 1.0
    use_guardrails: bool = False
