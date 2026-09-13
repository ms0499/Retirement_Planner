from pydantic import BaseModel


class ExpenseCategoryBase(BaseModel):
    category: str
    pre_retirement_annual: float = 0
    post_retirement_annual: float = 0


class ExpenseCategoryCreate(ExpenseCategoryBase):
    pass


class ExpenseCategoryOut(ExpenseCategoryBase):
    id: int
    household_id: int

    model_config = {"from_attributes": True}
