from sqlalchemy import select
from sqlalchemy.orm import Session

from app.students.students_model import StudentModel


class StudentsRepository:
    def find_all(self, db: Session) -> list[StudentModel]:
        stmt = select(StudentModel).order_by(StudentModel.createdAt.desc())
        return list(db.scalars(stmt).all())

    def find_by_id(self, db: Session, student_id: str) -> StudentModel | None:
        return db.get(StudentModel, student_id)

    def find_by_email(self, db: Session, email: str) -> StudentModel | None:
        stmt = select(StudentModel).where(StudentModel.email == email)
        return db.scalars(stmt).first()

    def find_by_username(self, db: Session, username: str) -> StudentModel | None:
        stmt = select(StudentModel).where(StudentModel.username == username)
        return db.scalars(stmt).first()

    def save(self, db: Session, student: StudentModel) -> StudentModel:
        db.add(student)
        db.flush()
        return student

    def delete(self, db: Session, student: StudentModel) -> None:
        db.delete(student)
        db.flush()


students_repository = StudentsRepository()
