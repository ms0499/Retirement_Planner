from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), nullable=False)

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    pre_retirement_annual: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    post_retirement_annual: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    household: Mapped["Household"] = relationship(back_populates="expense_categories")
