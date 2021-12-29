<p align="center">
<a href="https://github.com/aminalaee/sqladmin">
    <img width="400px" src="https://raw.githubusercontent.com/aminalaee/sqladmin/main/docs/assets/images/banner.png" alt"SQLAdmin">
</a>
</p>

<p align="center">
<a href="https://github.com/aminalaee/sqladmin/actions">
    <img src="https://github.com/aminalaee/sqladmin/workflows/Test%20Suite/badge.svg" alt="Build Status">
</a>
<a href="https://github.com/aminalaee/sqladmin/actions">
    <img src="https://github.com/aminalaee/sqladmin/workflows/Publish/badge.svg" alt="Publish Status">
</a>
<a href="https://codecov.io/gh/aminalaee/sqladmin">
    <img src="https://codecov.io/gh/aminalaee/sqladmin/branch/main/graph/badge.svg" alt="Coverage">
</a>
<a href="https://pypi.org/project/sqladmin/">
    <img src="https://badge.fury.io/py/sqladmin.svg" alt="Package version">
</a>
<a href="https://pypi.org/project/sqladmin" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/sqladmin.svg?color=%2334D058" alt="Supported Python versions">
</a>
</p>

---

# SQLAlchemy Admin dashboard

SQLAdmin is a flexible Admin interface for SQLAlchemy models.

Main features include:

* SQLAlchemy sync/async engines
* [Starlette](https://github.com/encode/starlette) integration
* [FastAPI](https://github.com/tiangolo/fastapi) integration
* Modern UI using [Tabler](https://github.com/tabler/tabler)

---

**Documentation**: [https://aminalaee.github.io/sqladmin](https://aminalaee.github.io/sqladmin)

**Source Code**: [https://github.com/encode/starlette](https://github.com/encode/starlette)

**Online Demo**: [Demo](https://python-sqladmin.herokuapp.com/admin/)

---

## Installation

```shell
$ pip install sqladmin
```

---

## Quickstart

Let's define an example SQLAlchemy model:

```python
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


Base = declarative_base()
engine = create_engine(
    "sqlite:///example.db",
    connect_args={"check_same_thread": False},
)
Session = sessionmaker(bind=engine)
db = Session()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)


Base.metadata.create_all(engine)  # Create tables
```

If you want to use `SQLAdmin` with `FastAPI`:

```python
from fastapi import FastAPI
from sqladmin import Admin, ModelAdmin


app = FastAPI()
admin = Admin(app, db)


class UserAdmin(ModelAdmin, model=User):
    list_display = [User.id, User.name]


admin.register_model(UserAdmin)
```

Or if you want to use `SQLAdmin` with `Starlette`:

```python
from starlette.applications import Starlette
from sqladmin import Admin, ModelAdmin


app = Starlette()
admin = Admin(app, db)


class UserAdmin(ModelAdmin, model=User):
    list_display = [User.id, User.name]


admin.register_model(UserAdmin)
```

Now visiting `/admin` on your browser you can see the `SQLAdmin` interface.
