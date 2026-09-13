from pydantic import BaseModel

from app.models.account import AccountType


class AccountBase(BaseModel):
    name: str
    account_type: AccountType
    balance: float = 0
    annual_contribution: float = 0
    annual_employer_match: float = 0
    expected_return_override: float | None = None
    person_id: int | None = None


class AccountCreate(AccountBase):
    pass


class AccountOut(AccountBase):
    id: int
    household_id: int

    model_config = {"from_attributes": True}
