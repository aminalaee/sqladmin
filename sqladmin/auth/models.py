from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):  # type: ignore
    __tablename__ = "auth_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(length=128), unique=True)
    email = Column(String(length=128))
    password = Column(String(length=128))
    is_active = Column(Boolean, default=True)
    # is_superuser = Column(Boolean)
