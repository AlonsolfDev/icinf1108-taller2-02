from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.pets.pets_model import PetModel
from app.pets.pets_repository import PetsRepository, pets_repository
from app.pets.pets_schemas import CreatePetDto, Pet, PetList, UpdatePetDto
from app.shared.datetimes import utc_now
from app.shared.exceptions import conflict
from app.shared.transactions import transaction
from app.students.students_service import StudentsService, students_service


class PetsService:
    def __init__(self, repository: PetsRepository, students: StudentsService) -> None:
        self.repository = repository
        self.students_service = students

    def find_all_for_student(self, db: Session, student_id: str) -> PetList:
        self.students_service.find_by_id(db, student_id)
        pets = self.repository.find_all_by_student(db, student_id)
        return PetList(total=len(pets), items=[Pet.model_validate(pet) for pet in pets])

    def create(self, db: Session, student_id: str, data: CreatePetDto) -> Pet:
        with transaction(db):
            self.students_service.find_by_id(db, student_id)
            self.assert_no_conflicts(db, student_id, data)
            now = utc_now()
            pet = PetModel(
                id=str(uuid4()),
                studentId=student_id,
                name=data.name,
                species=data.species,
                age=data.age,
                createdAt=now,
                updatedAt=now,
            )
            self.repository.save(db, pet)
            result = Pet.model_validate(pet)
        return result

    def update(
        self, db: Session, student_id: str, pet_id: str, data: UpdatePetDto
    ) -> Pet:
        with transaction(db):
            pet = self.find_owned(db, student_id, pet_id)
            self.assert_no_conflicts(db, student_id, data, except_id=pet_id)
            for field, value in data.model_dump(exclude_none=True).items():
                setattr(pet, field, value)
            pet.updatedAt = utc_now()
            self.repository.save(db, pet)
            result = Pet.model_validate(pet)
        return result

    def delete(self, db: Session, student_id: str, pet_id: str) -> Pet:
        with transaction(db):
            pet = self.find_owned(db, student_id, pet_id)
            result = Pet.model_validate(pet)
            self.repository.delete(db, pet)
        return result

    def find_owned(self, db: Session, student_id: str, pet_id: str) -> PetModel:
        self.students_service.find_by_id(db, student_id)
        pet = self.repository.find_by_id(db, pet_id)
        if pet is None or pet.studentId != student_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mascota no encontrada"
            )
        return pet

    def assert_no_conflicts(
        self,
        db: Session,
        student_id: str,
        data: CreatePetDto | UpdatePetDto,
        except_id: str | None = None,
    ) -> None:
        if not data.name:
            return
        existing = self.repository.find_by_student_and_name(db, student_id, data.name)
        if existing and existing.id != except_id:
            raise conflict(
                {"name": {"message": "Ya tienes una mascota con ese nombre"}}
            )


pets_service = PetsService(pets_repository, students_service)
