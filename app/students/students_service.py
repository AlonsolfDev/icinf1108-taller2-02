from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.pets.pets_repository import PetsRepository, pets_repository
from app.pets.pets_schemas import Pet
from app.shared.datetimes import utc_now
from app.shared.exceptions import conflict
from app.shared.types import FieldErrors
from app.students.students_model import StudentModel
from app.students.students_repository import StudentsRepository, students_repository
from app.students.students_schemas import (
    CreateStudentDto,
    Student,
    StudentList,
    UpdateStudentDto,
)


class StudentsService:
    def __init__(self, repository: StudentsRepository, pets: PetsRepository) -> None:
        self.repository = repository
        self.pets_repository = pets

    def find_all(self, db: Session) -> StudentList:
        items = [Student.model_validate(s) for s in self.repository.find_all(db)]

        return StudentList(total=len(items), items=items)

    def find_by_id(self, db: Session, student_id: str) -> Student:
        return Student.model_validate(self._get_or_404(db, student_id))

    def create(self, db: Session, data: CreateStudentDto) -> Student:
        self.assert_no_conflicts(db, data)

        now = utc_now()
        student = StudentModel(
            id=str(uuid4()),
            name=data.name,
            username=data.username,
            email=data.email,
            age=data.age,
            createdAt=now,
            updatedAt=now,
        )

        self.repository.save(db, student)

        # Si una mascota falla, se lanza la excepción antes del commit y la sesión
        # hace rollback: el estudiante no queda creado. (Las mascotas siguen en
        # memoria hasta que Diego las migre a la BD.)
        for pet_data in data.pets:
            existing = self.pets_repository.find_by_student_and_name(
                student.id, pet_data.name
            )

            if existing is not None:
                raise conflict(
                    {"name": {"message": "Ya tienes una mascota con ese nombre"}}
                )

            pet_now = utc_now()
            pet = Pet(
                id=str(uuid4()),
                studentId=student.id,
                name=pet_data.name,
                species=pet_data.species,
                age=pet_data.age,
                createdAt=pet_now,
                updatedAt=pet_now,
            )

            self.pets_repository.save(pet)

        db.commit()
        db.refresh(student)

        return Student.model_validate(student)

    def update(self, db: Session, student_id: str, data: UpdateStudentDto) -> Student:
        existing = self._get_or_404(db, student_id)
        self.assert_no_conflicts(db, data, except_id=student_id)

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(existing, field, value)
        existing.updatedAt = utc_now()

        db.commit()
        db.refresh(existing)

        return Student.model_validate(existing)

    def delete(self, db: Session, student_id: str) -> Student:
        existing = self._get_or_404(db, student_id)
        deleted = Student.model_validate(existing)

        self.repository.delete(db, existing)
        db.commit()

        return deleted

    def assert_no_conflicts(
        self,
        db: Session,
        data: CreateStudentDto | UpdateStudentDto,
        except_id: str | None = None,
    ) -> None:
        errors: FieldErrors = {}

        if data.email:
            existing = self.repository.find_by_email(db, data.email)
            if existing and existing.id != except_id:
                errors["email"] = {"message": "El correo electrónico ya está en uso"}

        if data.username:
            existing = self.repository.find_by_username(db, data.username)
            if existing and existing.id != except_id:
                errors["username"] = {"message": "El nombre de usuario ya está en uso"}

        if errors:
            raise conflict(errors)

    def _get_or_404(self, db: Session, student_id: str) -> StudentModel:
        student = self.repository.find_by_id(db, student_id)

        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estudiante no encontrado",
            )

        return student


students_service = StudentsService(students_repository, pets_repository)