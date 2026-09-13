from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_household_member, require_household_owner
from app.models.household import Household, HouseholdMember, HouseholdRole
from app.models.user import User
from app.schemas.household import HouseholdMemberOut, HouseholdOut

router = APIRouter(prefix="/households", tags=["households"])


class InviteMember(BaseModel):
    email: EmailStr


@router.get("", response_model=list[HouseholdOut])
def list_my_households(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memberships = (
        db.query(HouseholdMember).filter(HouseholdMember.user_id == current_user.id).all()
    )
    return [m.household for m in memberships]


@router.get("/{household_id}", response_model=HouseholdOut)
def get_household(
    household_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    household = db.get(Household, household_id)
    if not household:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")
    return household


@router.get("/{household_id}/members", response_model=list[HouseholdMemberOut])
def list_members(
    household_id: int,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_member),
):
    members = (
        db.query(HouseholdMember).filter(HouseholdMember.household_id == household_id).all()
    )
    return [
        HouseholdMemberOut(id=m.id, user_id=m.user_id, email=m.user.email, role=m.role)
        for m in members
    ]


@router.post("/{household_id}/invite", response_model=HouseholdOut)
def invite_member(
    household_id: int,
    payload: InviteMember,
    db: Session = Depends(get_db),
    _membership: HouseholdMember = Depends(require_household_owner),
):
    invitee = db.query(User).filter(User.email == payload.email).first()
    if not invitee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user with that email — they need to register first",
        )
    existing = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.household_id == household_id, HouseholdMember.user_id == invitee.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already a member")

    membership = HouseholdMember(
        household_id=household_id, user_id=invitee.id, role=HouseholdRole.MEMBER
    )
    db.add(membership)
    db.commit()
    return db.get(Household, household_id)


@router.delete("/{household_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    household_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    _owner_membership: HouseholdMember = Depends(require_household_owner),
):
    member = db.get(HouseholdMember, member_id)
    if not member or member.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if member.role == HouseholdRole.OWNER:
        other_owners = (
            db.query(HouseholdMember)
            .filter(
                HouseholdMember.household_id == household_id,
                HouseholdMember.role == HouseholdRole.OWNER,
                HouseholdMember.id != member.id,
            )
            .count()
        )
        if other_owners == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can't remove the household's only owner",
            )

    db.delete(member)
    db.commit()
