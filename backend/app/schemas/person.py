from pydantic import BaseModel

from app.models.person import Relationship


class PersonBase(BaseModel):
    name: str
    relationship_type: Relationship
    current_age: int
    retirement_age: int
    life_expectancy: int
    social_security_monthly_estimate: float = 0
    social_security_claim_age: int = 67
    pension_monthly: float = 0


class PersonCreate(PersonBase):
    pass


class PersonOut(PersonBase):
    id: int
    household_id: int

    model_config = {"from_attributes": True}
