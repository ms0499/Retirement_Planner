from pydantic import BaseModel

from app.models.household import HouseholdRole


class HouseholdOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class HouseholdMemberOut(BaseModel):
    id: int
    user_id: int
    email: str
    role: HouseholdRole

    model_config = {"from_attributes": True}
