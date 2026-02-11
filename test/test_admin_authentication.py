from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.services.auth_service import authenticate_admin_password

# Ensure SQLAlchemy relationships are fully registered for tests
import app.models.audit_log  # noqa: F401
import app.models.student_profile  # noqa: F401


def make_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session_local()


def create_admin(db, student_number: str = "00000000", password: str = "admin123"):
    admin_role = Role(name="admin", description="مدیر")
    db.add(admin_role)
    db.flush()

    admin = User(
        student_number=student_number,
        hashed_password=hash_password(password),
        role_id=admin_role.id,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def test_authenticate_admin_password_accepts_correct_password():
    db = make_db_session()
    admin = create_admin(db)

    authenticated = authenticate_admin_password(db, "admin123")

    assert authenticated is not None
    assert authenticated.id == admin.id


def test_authenticate_admin_password_rejects_incorrect_password():
    db = make_db_session()
    create_admin(db)

    authenticated = authenticate_admin_password(db, "wrong-password")

    assert authenticated is None


def test_authenticate_admin_password_trims_whitespace_input():
    db = make_db_session()
    admin = create_admin(db, password="secret-pass")

    authenticated = authenticate_admin_password(db, "  secret-pass  ")

    assert authenticated is not None
    assert authenticated.id == admin.id