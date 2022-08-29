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

# SQLAlchemy Admin for Starlette/FastAPI

SQLAdmin is a flexible Admin interface for SQLAlchemy models.

Main features include:

* [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy) sync/async engines
* [Starlette](https://github.com/encode/starlette) integration
* [FastAPI](https://github.com/tiangolo/fastapi) integration
* [SQLModel](https://github.com/tiangolo/sqlmodel) support
* Modern UI using [Tabler](https://github.com/tabler/tabler)

---

**Documentation**: [https://aminalaee.dev/sqladmin](https://aminalaee.dev/sqladmin)

**Source Code**: [https://github.com/aminalaee/sqladmin](https://github.com/aminalaee/sqladmin)

**Online Demo**: [Demo](https://sqladmin-demo.aminalaee.dev/admin/)

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


Base = declarative_base()
engine = create_engine(
    "sqlite:///example.db",
    connect_args={"check_same_thread": False},
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)


Base.metadata.create_all(engine)  # Create tables
```

If you want to use `SQLAdmin` with `FastAPI`:

```python
from fastapi import FastAPI
from sqladmin import Admin, ModelView


app = FastAPI()
admin = Admin(app, engine)


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.name]


admin.add_view(UserAdmin)
```

Or if you want to use `SQLAdmin` with `Starlette`:

```python
from sqladmin import Admin, ModelView
from starlette.applications import Starlette


app = Starlette()
admin = Admin(app, engine)


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.name]


admin.add_view(UserAdmin)
```

Now visiting `/admin` on your browser you can see the `SQLAdmin` interface.

## Related projects and inspirations

* [Flask-Admin](https://github.com/flask-admin/flask-admin) Admin interface for Flask supporting different database backends and ORMs. This project has inspired SQLAdmin extensively and most of the features and configurations are implemented the same.
* [FastAPI-Admin](https://github.com/fastapi-admin/fastapi-admin) Admin interface for FastAPI which works with `TortoiseORM`.
* [Dashboard](https://github.com/encode/dashboard) Admin interface for ASGI frameworks which works with the `orm` package.
