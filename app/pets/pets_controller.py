from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.pets.pets_schemas import CreatePetDto, Pet, PetList, UpdatePetDto
from app.pets.pets_service import pets_service
from app.shared.database import get_db

router = APIRouter(prefix="/api/students/{studentId}/pets", tags=["Pets"])


@router.get("")
def find_all(studentId: str, db: Session = Depends(get_db)) -> PetList:
    return pets_service.find_all_for_student(db, studentId)


@router.post("", status_code=201)
def create(studentId: str, body: CreatePetDto, db: Session = Depends(get_db)) -> Pet:
    return pets_service.create(db, studentId, body)


@router.patch("/{petId}")
def update(
    studentId: str, petId: str, body: UpdatePetDto, db: Session = Depends(get_db)
) -> Pet:
    return pets_service.update(db, studentId, petId, body)


@router.delete("/{petId}")
def delete(studentId: str, petId: str, db: Session = Depends(get_db)) -> Pet:
    return pets_service.delete(db, studentId, petId)
