# app/core/database.py
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

# تنظیمات دیتابیس
DATABASE_URL = "sqlite:///./basij.db"  # تغییر نام فایل برای مشخص‌تر بودن

# ایجاد engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # برای SQLite ضروری است
    echo=True  # اضافه کردن echo برای دیباگ - در production غیرفعال کنید
)

# ایجاد session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class برای مدل‌ها
Base = declarative_base()


# تابع کمکی برای ایجاد دیتابیس
def ensure_student_profiles_schema():
    """اطمینان از همگام بودن ستون‌های جدول student_profiles با مدل."""
    inspector = inspect(engine)
    if "student_profiles" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("student_profiles")}
    pending_columns = []

    if "first_name" not in existing_columns:
        pending_columns.append(("first_name", "VARCHAR(50) NOT NULL DEFAULT ''"))
    if "last_name" not in existing_columns:
        pending_columns.append(("last_name", "VARCHAR(50) NOT NULL DEFAULT ''"))
    if "student_number" not in existing_columns:
        pending_columns.append(("student_number", "VARCHAR(20) NOT NULL DEFAULT ''"))
    if "has_authenticated" not in existing_columns:
        pending_columns.append(("has_authenticated", "BOOLEAN NOT NULL DEFAULT 0"))

    if not pending_columns:
        return

    with engine.begin() as connection:
        for column_name, column_ddl in pending_columns:
            connection.execute(
                text(f"ALTER TABLE student_profiles ADD COLUMN {column_name} {column_ddl}")
            )


def create_database():
    """ایجاد همه جداول در دیتابیس"""
    Base.metadata.create_all(bind=engine)
    ensure_student_profiles_schema()
    print(f"✅ دیتابیس در {DATABASE_URL} ایجاد شد")


# تابع کمکی برای دیدن جداول ایجاد شده
def show_tables():
    """نمایش جداول ایجاد شده در دیتابیس"""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("\n📊 جداول موجود در دیتابیس:")
    for table in tables:
        print(f"  - {table}")
        columns = inspector.get_columns(table)
        for column in columns:
            print(f"    ├─ {column['name']}: {column['type']}")

    return tables