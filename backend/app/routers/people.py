from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_household_member
from app.models.household import HouseholdMember
from app.models.person import Person
from app.schemas.person import PersonCreate, PersonOut

router = APIRouter(prefix="/households/{household_id}/people", tags=["people"])


@router.get("", response_model=list[PersonOut])
def list_people(
    household_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    return db.query(Person).filter(Person.household_id == household_id).all()


@router.post("", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
def create_person(
    household_id: int,
    payload: PersonCreate,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    person = Person(household_id=household_id, **payload.model_dump())
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.put("/{person_id}", response_model=PersonOut)
def update_person(
    household_id: int,
    person_id: int,
    payload: PersonCreate,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    person = db.get(Person, person_id)
    if not person or person.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    for key, value in payload.model_dump().items():
        setattr(person, key, value)
    db.commit()
    db.refresh(person)
    return person


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(
    household_id: int,
    person_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    person = db.get(Person, person_id)
    if not person or person.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    db.delete(person)
    db.commit()
