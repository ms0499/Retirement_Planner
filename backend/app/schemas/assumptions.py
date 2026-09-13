from pydantic import BaseModel

from app.models.assumptions import FilingStatus, LifestylePreset


class AssumptionsBase(BaseModel):
    inflation_rate: float
    expected_return: float
    safe_withdrawal_rate: float
    lifestyle_preset: LifestylePreset
    filing_status: FilingStatus


class AssumptionsUpdate(BaseModel):
    inflation_rate: float | None = None
    expected_return: float | None = None
    safe_withdrawal_rate: float | None = None
    lifestyle_preset: LifestylePreset | None = None
    filing_status: FilingStatus | None = None


class AssumptionsOut(AssumptionsBase):
    id: int
    household_id: int

    model_config = {"from_attributes": True}
