"""Initialize the database with the default admin user."""

import logging

from auth_utils import get_password_hash
from constants import ROLE_ADMIN
from database import Base, SessionLocal, User, engine

logger = logging.getLogger(__name__)
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin@12345"

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    admin_user = db.query(User).filter(User.username == DEFAULT_ADMIN_USERNAME).first()
    if not admin_user:
        db.add(User(username=DEFAULT_ADMIN_USERNAME, password_hash=get_password_hash(DEFAULT_ADMIN_PASSWORD), role=ROLE_ADMIN, mfa_enabled=False))
        db.commit()
        logger.info("Default admin user created: username=%s", DEFAULT_ADMIN_USERNAME)
    else:
        logger.info("Default admin user already exists")
finally:
    db.close()
