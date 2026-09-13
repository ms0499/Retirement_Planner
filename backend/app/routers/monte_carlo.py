from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.constants import MONTE_CARLO_DEFAULT_RETURN_VOLATILITY, MONTE_CARLO_DEFAULT_SIMULATIONS
from app.database import get_db
from app.deps import load_plan_inputs, require_household_member
from app.models.household import HouseholdMember
from app.schemas.projection import MonteCarloOut
from app.services.monte_carlo import run_monte_carlo

router = APIRouter(prefix="/households/{household_id}/monte-carlo", tags=["monte-carlo"])


@router.get("", response_model=MonteCarloOut)
def get_monte_carlo(
    household_id: int,
    num_simulations: int = Query(MONTE_CARLO_DEFAULT_SIMULATIONS, ge=100, le=2000),
    return_volatility: float = Query(MONTE_CARLO_DEFAULT_RETURN_VOLATILITY, ge=0.0, le=0.5),
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    people, accounts, expenses, assumptions = load_plan_inputs(household_id, db)
    return run_monte_carlo(
        people, accounts, expenses, assumptions, num_simulations, return_volatility
    )
