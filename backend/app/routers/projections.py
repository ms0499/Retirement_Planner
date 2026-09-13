from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import load_plan_inputs, require_household_member
from app.models.household import HouseholdMember
from app.schemas.projection import ProjectionOut
from app.services.calculations import build_projection

router = APIRouter(prefix="/households/{household_id}/projection", tags=["projection"])


@router.get("", response_model=ProjectionOut)
def get_projection(
    household_id: int,
    use_guardrails: bool = False,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    people, accounts, expenses, assumptions = load_plan_inputs(household_id, db)
    return build_projection(people, accounts, expenses, assumptions, use_guardrails=use_guardrails)
