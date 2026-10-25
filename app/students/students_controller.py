from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.pets.pets_service import pets_service
from app.shared.database import get_db
from app.students.students_schemas import (
    CreateStudentDto,
    Student,
    StudentList,
    UpdateStudentDto,
)
from app.students.students_service import students_service

router = APIRouter(prefix="/api/students", tags=["Students"])


@router.get("")
def find_all(db: Session = Depends(get_db)) -> StudentList:
    return students_service.find_all(db)


@router.get("/{studentId}")
def find_by_id(studentId: str, db: Session = Depends(get_db)) -> Student:
    return students_service.find_by_id(db, studentId)


@router.post("", status_code=201)
def create(body: CreateStudentDto, db: Session = Depends(get_db)) -> Student:
    return students_service.create(db, body)


@router.patch("/{studentId}")
def update(
    studentId: str, body: UpdateStudentDto, db: Session = Depends(get_db)
) -> Student:
    return students_service.update(db, studentId, body)


@router.delete("/{studentId}")
def delete(studentId: str, db: Session = Depends(get_db)) -> Student:
    pets_service.delete_all_for_student(studentId)
    deleted = students_service.delete(db, studentId)
    return deleted
