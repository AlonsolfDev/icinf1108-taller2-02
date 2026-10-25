from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.shared.exceptions import conflict


@contextmanager
def transaction(db: Session) -> Generator[None]:
    """Confirma la operación completa o revierte todas sus escrituras."""
    try:
        yield
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        diagnostic = getattr(exc.orig, "diag", None)
        constraint = getattr(diagnostic, "constraint_name", None)
        messages = {
            "students_email_key": ("email", "El correo electrónico ya está en uso"),
            "students_username_key": (
                "username",
                "El nombre de usuario ya está en uso",
            ),
            "uq_pets_student_name": ("name", "Ya tienes una mascota con ese nombre"),
        }
        if constraint in messages:
            field, message = messages[constraint]
            raise conflict({field: {"message": message}}) from exc
        raise
    except Exception:
        db.rollback()
        raise
