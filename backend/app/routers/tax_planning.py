from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import load_plan_inputs, require_household_member
from app.models.household import HouseholdMember
from app.schemas.projection import RothConversionOpportunitiesOut, SocialSecurityComparisonOut
from app.services.calculations import roth_conversion_opportunities
from app.services.social_security import compare_claiming_ages

router = APIRouter(prefix="/households/{household_id}", tags=["tax-planning"])


@router.get("/social-security-comparison", response_model=SocialSecurityComparisonOut)
def get_social_security_comparison(
    household_id: int,
    person_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    people, accounts, expenses, assumptions = load_plan_inputs(household_id, db)
    try:
        return compare_claiming_ages(people, accounts, expenses, assumptions, person_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/roth-conversion-opportunities", response_model=RothConversionOpportunitiesOut)
def get_roth_conversion_opportunities(
    household_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    people, accounts, expenses, assumptions = load_plan_inputs(household_id, db)
    return roth_conversion_opportunities(people, accounts, expenses, assumptions)
