SQLAdmin configuration options are heavily inspired by the Flask-Admin project.

This page will give you a basic introduction and for all the details
you can visit [API Reference](./api_reference/model_admin.md).

Let's say you've defined your SQLAlchemy models like this:

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

If you want to integrate SQLAdmin into FastAPI application:

```python
from fastapi import FastAPI
from sqladmin import Admin, ModelAdmin


app = FastAPI()
admin = Admin(app, engine)


class UserAdmin(ModelAdmin, model=User):
    column_list = [User.id, User.name]


admin.register_model(UserAdmin)
```

As you can see the `UserAdmin` class inherits from `ModelAdmin` and accepts some configurations.

## Permissions

You can configure a few general permissions for this model.
The following options are available:

* `can_create`: If the model can create new instances via SQLAdmin.
* `can_edit`: If the model instances can be edited via SQLAdmin.
* `can_delete`: If the model instances can be deleted via SQLAdmin.
* `can_view_details`: If the model instance details can be viewed via SQLAdmin.

!!! example

    ```python
    class UserAdmin(ModelAdmin, model=User):
        can_create = True
        can_edit = True
        can_delete = False
        can_view_details = True
    ```

## Metadata

The metadata for the model. The options are:

* `name`: Display name for this model. Default value is the class name.
* `name_plural`: Display plural name for this model. Default value is class name + `s`.
* `icon`: Icon to be displayed for this model in the admin. Only FontAwesome names are supported.

!!! example

    ```python
    class UserAdmin(ModelAdmin, model=User):
        name = "User"
        name_plural = "Users"
        icon = "fas fa-user"
    ```

## List page

These options allow configurations in the list page, in the case of this example
where you can view list of User records.

The options available are:

* `column_list`: List of columns or column names to be displayed in the list page.
* `column_exclude_list`: List of columns or column names to be excluded in the list page.

!!! example

    ```python
    class UserAdmin(ModelAdmin, model=User):
        column_list = [User.id, User.name]
        # column_list = ["id", "name"]
    ```

    ```python
    class UserAdmin(ModelAdmin, model=User):
        column_exclude_list = [User.id]
    ```

## Details page

These options allow configurations in the details page, in the case of this example
where you can view details of a single User.

The options available are:

* `column_details_list`: List of columns or column names to be displayed in the details page.
* `column_details_exclude_list`: List of columns or column names to be excluded in the details page.

!!! example

    ```python
    class UserAdmin(ModelAdmin, model=User):
        column_details_list = [User.id, User.name]
    ```

    ```python
    class UserAdmin(ModelAdmin, model=User):
        column_details_exclude_list = [User.id]
    ```

## Pagination options

The pagination options in the list page can be configured. The available options include:

* `page_size`: Default page size in pagination. Default is `10`.
* `page_size_options`: Pagination selector options. Default is `[10, 25, 50, 100]`.

!!! example

    ```python
    class UserAdmin(ModelAdmin, model=User):
        page_size = 50
        page_size_options = [25, 50, 100, 200]
    ```

## Templates

The template files are built using Jinja2 and can be completely overriden in the configurations.
The pages available are:

* `list_template`: Template to use for models list page. Default is `list.html`.
* `create_template`: Template to use for model creation page. Default is `create.html`.
* `details_template`: Template to use for model details page. Default is `details.html`.
* `edit_template`: Template to use for model edit page. Default is `edit.html`.

!!! example

    ```python
    class UserAdmin(ModelAdmin, model=User):
        list_template = "custom_list.html"
    ```

For more information about working with template see [Working with Templates](./working_with_templates.md).
