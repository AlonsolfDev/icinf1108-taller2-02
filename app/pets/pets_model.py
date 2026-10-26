from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base

if TYPE_CHECKING:
    from app.students.students_model import StudentModel


class PetModel(Base):
    __tablename__ = "pets"
    __table_args__ = (
        UniqueConstraint("student_id", "name", name="uq_pets_student_name"),
        CheckConstraint("age IS NULL OR (age >= 0 AND age <= 100)", name="ck_pets_age"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    studentId: Mapped[str] = mapped_column(
        "student_id",
        String(36),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(
        "created_at", DateTime(timezone=True), nullable=False
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updated_at", DateTime(timezone=True), nullable=False
    )
    student: Mapped["StudentModel"] = relationship(back_populates="pets")
