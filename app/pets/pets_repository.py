from sqlalchemy import select
from sqlalchemy.orm import Session

from app.pets.pets_model import PetModel


class PetsRepository:
    def find_all_by_student(self, db: Session, student_id: str) -> list[PetModel]:
        stmt = (
            select(PetModel)
            .where(PetModel.studentId == student_id)
            .order_by(PetModel.createdAt.desc())
        )
        return list(db.scalars(stmt).all())

    def find_by_id(self, db: Session, pet_id: str) -> PetModel | None:
        return db.get(PetModel, pet_id)

    def find_by_student_and_name(
        self, db: Session, student_id: str, name: str
    ) -> PetModel | None:
        stmt = select(PetModel).where(
            PetModel.studentId == student_id, PetModel.name == name
        )
        return db.scalars(stmt).first()

    def save(self, db: Session, pet: PetModel) -> PetModel:
        db.add(pet)
        db.flush()
        return pet

    def delete(self, db: Session, pet: PetModel) -> None:
        db.delete(pet)
        db.flush()


pets_repository = PetsRepository()
