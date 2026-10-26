from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.pets.pets_model import PetModel
from app.pets.pets_repository import pets_repository
from app.shared.transactions import transaction
from app.students.students_model import StudentModel
from app.students.students_repository import students_repository


def payload(username="ana_test", pets=None):
    return {
        "name": "Ana Prueba",
        "username": username,
        "email": f"{username}@example.com",
        "age": 21,
        "pets": pets or [],
    }


def create_student(client, username="ana_test", pets=None):
    response = client.post("/api/students", json=payload(username, pets))
    assert response.status_code == 201, response.text
    return response.json()["data"]


def counts(test_engine):
    with Session(test_engine) as db:
        return (
            db.scalar(select(func.count()).select_from(StudentModel)),
            db.scalar(select(func.count()).select_from(PetModel)),
        )


def test_crud_persists_across_sessions(client, test_engine):
    student = create_student(client, pets=[{"name": "Michi", "species": "gato"}])
    sid = student["id"]
    path = f"/api/students/{sid}/pets"
    assert client.get("/api/students").json()["data"]["total"] == 1
    pet = client.get(path).json()["data"]["items"][0]
    created = client.post(path, json={"name": "Firulais", "species": "perro", "age": 3})
    assert created.status_code == 201
    changed = client.patch(
        f"{path}/{pet['id']}", json={"name": "Michi nuevo", "age": 2}
    )
    assert changed.status_code == 200
    assert changed.json()["data"]["name"] == "Michi nuevo"
    assert changed.json()["data"]["updatedAt"] >= pet["updatedAt"]
    updated = client.patch(f"/api/students/{sid}", json={"name": "Ana Actualizada"})
    assert updated.status_code == 200
    with Session(test_engine) as db:
        stored = db.get(StudentModel, sid)
        assert stored.name == "Ana Actualizada"
        assert stored.updatedAt >= stored.createdAt
        assert db.get(PetModel, pet["id"]).age == 2
        assert len(stored.pets) == 2
    assert client.delete(f"{path}/{pet['id']}").status_code == 200
    assert client.get(path).json()["data"]["total"] == 1


def test_duplicate_pet_rolls_back_student_and_first_pet(client, test_engine):
    pets = [{"name": "Duplicada", "species": "gato"}] * 2
    response = client.post("/api/students", json=payload(pets=pets))
    assert response.status_code == 409
    assert counts(test_engine) == (0, 0)
    # El email y username del intento fallido siguen disponibles.
    create_student(client, pets=[pets[0]])
    assert counts(test_engine) == (1, 1)


def test_failure_after_pet_flush_rolls_back_everything(client, test_engine):
    original = pets_repository.save
    flushed = []

    def fail_after_flush(db, pet):
        original(db, pet)
        flushed.append(
            (
                db.scalar(select(func.count()).select_from(StudentModel)),
                db.scalar(select(func.count()).select_from(PetModel)),
            )
        )
        raise RuntimeError("Fallo simulado después de escribir en PostgreSQL")

    with patch.object(pets_repository, "save", side_effect=fail_after_flush):
        response = client.post(
            "/api/students", json=payload(pets=[{"name": "Michi", "species": "gato"}])
        )
    assert response.status_code == 500
    assert flushed == [(1, 1)]
    assert counts(test_engine) == (0, 0)
    create_student(client)


def test_student_deletion_cascades(client, test_engine):
    student = create_student(client, pets=[{"name": "Michi", "species": "gato"}])
    response = client.delete(f"/api/students/{student['id']}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == student["id"]
    assert counts(test_engine) == (0, 0)


def test_failed_deletion_restores_student_and_pets(client, test_engine):
    student = create_student(client, pets=[{"name": "Michi", "species": "gato"}])
    original = students_repository.delete
    flushed = []

    def fail_after_delete(db, model):
        original(db, model)
        flushed.append(
            (
                db.scalar(select(func.count()).select_from(StudentModel)),
                db.scalar(select(func.count()).select_from(PetModel)),
            )
        )
        raise RuntimeError("Fallo simulado después del borrado en cascada")

    with patch.object(students_repository, "delete", side_effect=fail_after_delete):
        response = client.delete(f"/api/students/{student['id']}")
    assert response.status_code == 500
    assert flushed == [(0, 0)]
    assert counts(test_engine) == (1, 1)


def test_uniqueness_and_pet_ownership(client):
    first = create_student(client, pets=[{"name": "Michi", "species": "gato"}])
    second = create_student(
        client, "otro_test", pets=[{"name": "Michi", "species": "gato"}]
    )
    first_path = f"/api/students/{first['id']}/pets"
    pet = client.get(first_path).json()["data"]["items"][0]
    assert (
        client.post(first_path, json={"name": "Michi", "species": "perro"}).status_code
        == 409
    )
    foreign = f"/api/students/{second['id']}/pets/{pet['id']}"
    assert client.patch(foreign, json={"name": "Robada"}).status_code == 404
    assert client.delete(foreign).status_code == 404
    assert client.post("/api/students", json=payload()).status_code == 409
    assert (
        client.post(
            "/api/students/inexistente/pets", json={"name": "Michi", "species": "gato"}
        ).status_code
        == 404
    )


def test_database_unique_constraint_returns_conflict(client, test_engine):
    student = create_student(client, pets=[{"name": "Michi", "species": "gato"}])
    with Session(test_engine) as db:
        existing = db.scalars(select(PetModel)).one()
        duplicate = PetModel(
            id="duplicate",
            studentId=student["id"],
            name="Michi",
            species="perro",
            createdAt=existing.createdAt,
            updatedAt=existing.updatedAt,
        )
        with pytest.raises(HTTPException) as exc:
            with transaction(db):
                pets_repository.save(db, duplicate)
        assert exc.value.status_code == 409
        assert db.scalar(select(func.count()).select_from(PetModel)) == 1


def test_validation_preserves_response_envelope(client):
    response = client.post(
        "/api/students",
        json=payload(pets=[{"name": "Michi", "species": "gato", "age": -1}]),
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == 400
    assert body["data"] is None
    assert "age" in body["errors"]
