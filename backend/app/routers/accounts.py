from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_household_member
from app.models.account import Account
from app.models.household import HouseholdMember
from app.schemas.account import AccountCreate, AccountOut

router = APIRouter(prefix="/households/{household_id}/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(
    household_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    return db.query(Account).filter(Account.household_id == household_id).all()


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    household_id: int,
    payload: AccountCreate,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    account = Account(household_id=household_id, **payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=AccountOut)
def update_account(
    household_id: int,
    account_id: int,
    payload: AccountCreate,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    account = db.get(Account, account_id)
    if not account or account.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    for key, value in payload.model_dump().items():
        setattr(account, key, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    household_id: int,
    account_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    account = db.get(Account, account_id)
    if not account or account.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    db.delete(account)
    db.commit()
