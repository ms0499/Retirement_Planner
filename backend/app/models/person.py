import enum

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Relationship(str, enum.Enum):
    SELF = "self"
    PARTNER = "partner"


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship_type: Mapped[Relationship] = mapped_column(
        Enum(Relationship, inherit_schema=True), nullable=False
    )

    current_age: Mapped[int] = mapped_column(Integer, nullable=False)
    retirement_age: Mapped[int] = mapped_column(Integer, nullable=False)
    life_expectancy: Mapped[int] = mapped_column(Integer, nullable=False)

    social_security_monthly_estimate: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    social_security_claim_age: Mapped[int] = mapped_column(Integer, default=67)
    pension_monthly: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    household: Mapped["Household"] = relationship(back_populates="people")
    accounts: Mapped[list["Account"]] = relationship(back_populates="person")
