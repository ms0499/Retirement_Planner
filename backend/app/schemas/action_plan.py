from pydantic import BaseModel


class ActionItem(BaseModel):
    priority: int
    category: str
    title: str
    description: str


class ActionPlanOut(BaseModel):
    is_on_track: bool
    money_lasts_to_year_index: int | None
    monte_carlo_success_rate: float
    items: list[ActionItem]
