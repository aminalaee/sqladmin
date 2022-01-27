from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from sqladmin.auth.hashers import make_password, verify_password

Base = declarative_base()


class User(Base):
    __tablename__ = "auth_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(length=128), unique=True)
    email = Column(String(length=128))
    password = Column(String(length=128))
    is_active = Column(Boolean, default=True)

    # is_superuser = Column(Boolean)

    def set_password(self, raw_password: str):
        self.password = make_password(
            raw_password,
        )

    def verify_password(self, raw_password: str) -> bool:
        return verify_password(
            raw_password,
            self.password,
        )
