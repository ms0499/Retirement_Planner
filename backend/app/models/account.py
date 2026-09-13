import enum

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccountType(str, enum.Enum):
    TRADITIONAL_401K = "traditional_401k"
    ROTH_401K = "roth_401k"
    TRADITIONAL_IRA = "traditional_ira"
    ROTH_IRA = "roth_ira"
    HSA = "hsa"
    BROKERAGE = "brokerage"
    CASH = "cash"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), nullable=False)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    balance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    annual_contribution: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    annual_employer_match: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    expected_return_override: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)

    household: Mapped["Household"] = relationship(back_populates="accounts")
    person: Mapped["Person | None"] = relationship(back_populates="accounts")
