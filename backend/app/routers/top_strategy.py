from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import load_plan_inputs, require_household_member
from app.models.household import HouseholdMember
from app.schemas.top_strategy import TopStrategyOut
from app.services.top_strategy import find_top_strategy

router = APIRouter(prefix="/households/{household_id}/top-strategy", tags=["top-strategy"])


@router.get("", response_model=TopStrategyOut)
def get_top_strategy(
    household_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    people, accounts, expenses, assumptions = load_plan_inputs(household_id, db)
    return find_top_strategy(people, accounts, expenses, assumptions)
