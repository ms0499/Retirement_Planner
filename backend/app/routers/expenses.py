from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_household_member
from app.models.expense import ExpenseCategory
from app.models.household import HouseholdMember
from app.schemas.expense import ExpenseCategoryCreate, ExpenseCategoryOut

router = APIRouter(prefix="/households/{household_id}/expenses", tags=["expenses"])


@router.get("", response_model=list[ExpenseCategoryOut])
def list_expenses(
    household_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    return db.query(ExpenseCategory).filter(ExpenseCategory.household_id == household_id).all()


@router.post("", response_model=ExpenseCategoryOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    household_id: int,
    payload: ExpenseCategoryCreate,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    expense = ExpenseCategory(household_id=household_id, **payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.put("/{expense_id}", response_model=ExpenseCategoryOut)
def update_expense(
    household_id: int,
    expense_id: int,
    payload: ExpenseCategoryCreate,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    expense = db.get(ExpenseCategory, expense_id)
    if not expense or expense.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    for key, value in payload.model_dump().items():
        setattr(expense, key, value)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    household_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    expense = db.get(ExpenseCategory, expense_id)
    if not expense or expense.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    db.delete(expense)
    db.commit()


@router.post("/seed-from-preset", response_model=list[ExpenseCategoryOut])
def seed_from_preset(
    household_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    """Prefill expense categories from the household's current lifestyle
    preset. Used during onboarding; safe to call only when no categories
    exist yet (won't duplicate on repeat calls)."""
    from app.models.assumptions import HouseholdAssumptions
    from app.services.lifestyle_presets import default_expense_categories_for_preset

    existing = db.query(ExpenseCategory).filter(ExpenseCategory.household_id == household_id).all()
    if existing:
        return existing

    assumptions = (
        db.query(HouseholdAssumptions)
        .filter(HouseholdAssumptions.household_id == household_id)
        .first()
    )
    if not assumptions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumptions not found")

    defaults = default_expense_categories_for_preset(assumptions.lifestyle_preset)
    created = []
    for entry in defaults:
        expense = ExpenseCategory(household_id=household_id, **entry)
        db.add(expense)
        created.append(expense)
    db.commit()
    for expense in created:
        db.refresh(expense)
    return created
