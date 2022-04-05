SQLadmin does not enforce any authentication backend to your application,
and will not implement a separate authentication system for you.

Instead it allows you to integrate any authentication system you'd like with it.

The `ModelAdmin` class in SQLAdmin implements two special methods you can override:

* `is_visible`
* `is_accessible`

As you might guesss the `is_visible` controls whether this Model
should be displayed in the menu or not.

The `is_accessible` controls whether or not this Model should be accessed.

Both methods implement the same signature and should return a boolean.

!!! note
    For Model to be displayed in the sidebar both `is_visible`
    and `is_accessible` should return `True`.

So in order to override these methods:

```python
from starlette.requests import Request


class UserAdmin(ModelAdmin, model=User):
    def is_accessible(self, request: Request) -> bool:
        # Do any check you need with the incoming request; for example check headers
        return True

    def is_visible(self, request: Request) -> bool:
        # Do any check you need with the incoming request; for example check headers
        return True
```

??? example "Full Example"
    ```python
    from sqladmin import Admin, ModelAdmin
    from sqlalchemy import Column, Integer, String, create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from starlette.applications import Starlette
    from starlette.requests import Request


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

    app = Starlette()
    admin = Admin(app, engine)


    class UserAdmin(ModelAdmin, model=User):
        def is_visible(self, request: Request) -> bool:
            return True

        def is_accessible(self, request: Request) -> bool:
            return True


    admin.register_model(UserAdmin)
    ```

Or in some cases you might want to apply authentication to the whole admin application.
In that case you might want to do something like:

```python
class AuthModelAdmin(ModelAdmin):
    def is_accessible(self, request: Request) -> bool:
        return True

    def is_visible(self, request: Request) -> bool:
        return True


class UserAdmin(AuthModelAdmin, model=User):
    list_display = [User.id, User.name]


class AddressAdmin(AuthModelAdmin, model=Address):
    list_display = [Address.id]
```

## Authentication Backend

You can integrate the Starlette [Authentication](https://www.starlette.io/authentication/)
backend into SQLadmin :

```python
from sqladmin import Admin, ModelAdmin
from starlette.applications import Starlette
from starlette.requests import Request

# AuthenticationMiddleware explained in Starlette docs

middlewares = [
    Middleware(AuthenticationMiddleware, backend=BasicAuthBackend())
]

app = Starlette()
admin = Admin(app=app, engine=engine, middlewares=middlewares)


class AuthModelAdmin(ModelAdmin):
    def is_accessible(self, request: Request) -> bool:
        # With Authentication backend you can now access request.user.
        if request.user.is_authenticated:
            return True
        return False
```

With the `middlewares` argument in SQLAdmin you can have full control over the
`Admin` created and you can mofiy the behaviour. For example you can implement a SessionMiddleware:

```python
from sqladmin import Admin
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware


app = Starlette()
admin = Admin(app=app, engine=engine, middlewares=[SessionMiddleware(...)])
```
