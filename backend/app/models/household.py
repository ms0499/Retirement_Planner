import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HouseholdRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class Household(Base):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    members: Mapped[list["HouseholdMember"]] = relationship(
        back_populates="household", cascade="all, delete-orphan"
    )
    people: Mapped[list["Person"]] = relationship(
        back_populates="household", cascade="all, delete-orphan"
    )
    accounts: Mapped[list["Account"]] = relationship(
        back_populates="household", cascade="all, delete-orphan"
    )
    expense_categories: Mapped[list["ExpenseCategory"]] = relationship(
        back_populates="household", cascade="all, delete-orphan"
    )
    assumptions: Mapped["HouseholdAssumptions | None"] = relationship(
        back_populates="household", cascade="all, delete-orphan", uselist=False
    )


class HouseholdMember(Base):
    __tablename__ = "household_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[HouseholdRole] = mapped_column(
        Enum(HouseholdRole), default=HouseholdRole.MEMBER, nullable=False
    )

    household: Mapped["Household"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
