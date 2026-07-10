from app.database import SessionLocal
from app.workflow.config import (
    DEPARTMENT_NAMES,
    REQUEST_TYPE_NAMES,
    STATUS_NAMES,
    ACTION_NAMES,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def department_name(code: str):
    return DEPARTMENT_NAMES.get(code, code or "-")

def request_type_name(code: str):
    return REQUEST_TYPE_NAMES.get(code, code or "-")

def status_name(code: str):
    return STATUS_NAMES.get(code, code or "-")

def action_name(code: str):
    return ACTION_NAMES.get(code, code or "-")