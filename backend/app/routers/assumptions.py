from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_household_member
from app.models.assumptions import HouseholdAssumptions
from app.models.household import HouseholdMember
from app.schemas.assumptions import AssumptionsOut, AssumptionsUpdate

router = APIRouter(prefix="/households/{household_id}/assumptions", tags=["assumptions"])


@router.get("", response_model=AssumptionsOut)
def get_assumptions(
    household_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    assumptions = (
        db.query(HouseholdAssumptions)
        .filter(HouseholdAssumptions.household_id == household_id)
        .first()
    )
    if not assumptions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumptions not found")
    return assumptions


@router.put("", response_model=AssumptionsOut)
def update_assumptions(
    household_id: int,
    payload: AssumptionsUpdate,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    assumptions = (
        db.query(HouseholdAssumptions)
        .filter(HouseholdAssumptions.household_id == household_id)
        .first()
    )
    if not assumptions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumptions not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(assumptions, key, value)
    db.commit()
    db.refresh(assumptions)
    return assumptions
