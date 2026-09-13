import enum

from sqlalchemy import Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import (
    DEFAULT_EXPECTED_RETURN,
    DEFAULT_INFLATION_RATE,
    DEFAULT_SAFE_WITHDRAWAL_RATE,
)
from app.database import Base


class LifestylePreset(str, enum.Enum):
    MODEST = "modest"
    COMFORTABLE = "comfortable"
    LUXURIOUS = "luxurious"
    CUSTOM = "custom"


class FilingStatus(str, enum.Enum):
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"


class HouseholdAssumptions(Base):
    __tablename__ = "household_assumptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id"), unique=True, nullable=False
    )

    inflation_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=DEFAULT_INFLATION_RATE)
    expected_return: Mapped[float] = mapped_column(Numeric(5, 4), default=DEFAULT_EXPECTED_RETURN)
    safe_withdrawal_rate: Mapped[float] = mapped_column(
        Numeric(5, 4), default=DEFAULT_SAFE_WITHDRAWAL_RATE
    )
    lifestyle_preset: Mapped[LifestylePreset] = mapped_column(
        Enum(LifestylePreset, inherit_schema=True), default=LifestylePreset.COMFORTABLE
    )
    filing_status: Mapped[FilingStatus] = mapped_column(
        Enum(FilingStatus, inherit_schema=True),
        default=FilingStatus.MARRIED_FILING_JOINTLY,
    )

    household: Mapped["Household"] = relationship(back_populates="assumptions")
