from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import load_plan_inputs, require_household_member
from app.models.household import HouseholdMember
from app.schemas.projection import ProjectionOut
from app.schemas.whatif import WhatIfInput
from app.services.whatif import run_what_if

router = APIRouter(prefix="/households/{household_id}/what-if", tags=["what-if"])


@router.post("", response_model=ProjectionOut)
def post_what_if(
    household_id: int,
    payload: WhatIfInput,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    people, accounts, expenses, assumptions = load_plan_inputs(household_id, db)
    return run_what_if(people, accounts, expenses, assumptions, payload)
