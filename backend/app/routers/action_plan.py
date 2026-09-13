from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import load_plan_inputs, require_household_member
from app.models.household import HouseholdMember
from app.schemas.action_plan import ActionPlanOut
from app.services.action_plan import build_action_plan

router = APIRouter(prefix="/households/{household_id}/action-plan", tags=["action-plan"])


@router.get("", response_model=ActionPlanOut)
def get_action_plan(
    household_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    people, accounts, expenses, assumptions = load_plan_inputs(household_id, db)
    return build_action_plan(people, accounts, expenses, assumptions)
