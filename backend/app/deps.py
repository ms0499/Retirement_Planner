from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.account import Account
from app.models.assumptions import HouseholdAssumptions
from app.models.expense import ExpenseCategory
from app.models.household import HouseholdMember, HouseholdRole
from app.models.person import Person
from app.models.user import User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    email = decode_access_token(token)
    if email is None:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def require_household_member(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HouseholdMember:
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == current_user.id,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a household member")
    return membership


def require_household_owner(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HouseholdMember:
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == current_user.id,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a household member")
    if membership.role != HouseholdRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only a household owner can do this"
        )
    return membership


def load_plan_inputs(
    household_id: int, db: Session
) -> tuple[list[Person], list[Account], list[ExpenseCategory], HouseholdAssumptions]:
    """Shared loader for anything that runs a projection: people, accounts,
    expenses, and assumptions for a household, with the same 400/404s every
    such endpoint should return when the household isn't ready yet."""
    people = db.query(Person).filter(Person.household_id == household_id).all()
    if not people:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add at least one person before running this analysis",
        )
    accounts = db.query(Account).filter(Account.household_id == household_id).all()
    expenses = db.query(ExpenseCategory).filter(ExpenseCategory.household_id == household_id).all()
    assumptions = (
        db.query(HouseholdAssumptions)
        .filter(HouseholdAssumptions.household_id == household_id)
        .first()
    )
    if not assumptions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumptions not found")
    return people, accounts, expenses, assumptions
