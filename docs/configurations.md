SQLAdmin configuration options are heavily inspired by the Flask-Admin project.

This page will give you a basic introduction and for all the details
you can visit [API Reference](./api_reference/model_view.md).

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
    email = Column(String)


Base.metadata.create_all(engine)  # Create tables
```

If you want to integrate SQLAdmin into FastAPI application:

```python
from fastapi import FastAPI
from sqladmin import Admin, ModelView


app = FastAPI()
admin = Admin(app, engine)


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.name]


admin.add_view(UserAdmin)
```

As you can see the `UserAdmin` class inherits from `ModelView` and accepts some configurations.

## Permissions

You can configure a few general permissions for this model.
The following options are available:

* `can_create`: If the model can create new instances via SQLAdmin. Default value is `True`.
* `can_edit`: If the model instances can be edited via SQLAdmin. Default value is `True`.
* `can_delete`: If the model instances can be deleted via SQLAdmin. Default value is `True`.
* `can_view_details`: If the model instance details can be viewed via SQLAdmin. Default value is `True`.
* `can_export`: If the model data can be exported in the list page. Default value is `True`.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
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
    class UserAdmin(ModelView, model=User):
        name = "User"
        name_plural = "Users"
        icon = "fa-solid fa-user"
    ```

## List page

These options allow configurations in the list page, in the case of this example
where you can view list of User records.

The options available are:

* `column_list`: List of columns or column names to be displayed in the list page.
* `column_exclude_list`: List of columns or column names to be excluded in the list page.
* `column_formatters`: Dictionary of column formatters in the list page.
* `column_searchable_list`: List of columns or column names to be searchable in the list page.
* `column_sortable_list`: List of columns or column names to be sortable in the list page.
* `column_default_sort`: Default sorting if no sorting is applied, tuple of (column, is_descending)
or list of the tuple for multiple columns.
* `list_query`: A SQLAlchemy `select` expression to use for model list page.
* `count_query`: A SQLAlchemy `select` expression to use for model count.
* `search_query`: A method with the signature of `(stmt, term) -> stmt` which can customize the search query.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        column_list = [User.id, User.name]
        # column_list = ["id", "name"]
    ```

    ```python
    class UserAdmin(ModelView, model=User):
        column_exclude_list = [User.id]
    ```

    ```python
    class UserAdmin(ModelView, model=User):
        column_searchable_list = [User.name]
        column_sortable_list = [User.id]
        column_formatters = {User.name: lambda m, a: m.name[:10]}
        column_default_sort = [(User.email, True), (User.name, False)]
    ```

## Details page

These options allow configurations in the details page, in the case of this example
where you can view details of a single User.

The options available are:

* `column_details_list`: List of columns or column names to be displayed in the details page.
* `column_details_exclude_list`: List of columns or column names to be excluded in the details page.
* `column_formatters_detail`: Dictionary of column formatters in the details page.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        column_details_list = [User.id, User.name]
    ```

    ```python
    class UserAdmin(ModelView, model=User):
        column_details_exclude_list = [User.id]
    ```

    ```python
    class UserAdmin(ModelView, model=User):
        column_formatters_detail = {User.name: lambda m, a: m.name[:10]}
    ```

## Pagination options

The pagination options in the list page can be configured. The available options include:

* `page_size`: Default page size in pagination. Default is `10`.
* `page_size_options`: Pagination selector options. Default is `[10, 25, 50, 100]`.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        page_size = 50
        page_size_options = [25, 50, 100, 200]
    ```

## General options

There are a few options which apply to both List and Detail pages. They include:

* `column_labels`: A mapping of column labels, used to map column names to new names in all places.
* `column_type_formatters`: A mapping of type keys and callable values to format in all places.
For example you can add custom date formatter to be used in both list and detail pages.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        def date_format(value):
            return value.strftime("%d.%m.%Y")

        column_labels = {User.mail: "Email"}
        column_type_formatters = dict(ModelView.column_type_formatters, date=date_format)
    ```

## Form options

SQLAdmin allows customizing how forms work with your models.
The forms are based on `WTForms` package and include the following options:

* `form`: Default form to be used for creating or editing the model. Default value is `None` and form is created dynamically.
* `form_base_class`: Default base class for creating forms. Default value is `wtforms.Form`.
* `form_args`: Dictionary of form field arguments supported by WTForms.
* `form_widget_args`: Dictionary of form widget rendering arguments supported by WTForms.
* `form_columns`: List of model columns to be included in the form. Default is all model columns.
* `form_excluded_columns`: List of model columns to be excluded from the form.
* `form_overrides`: Dictionary of form fields to override when creating the form.
* `form_include_pk`: Control if primary key column should be included in create/edit forms. Default is `False`.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        form_columns = [User.name]
        form_args = dict(name=dict(label="Full name"))
        form_widget_args = dict(email=dict(readonly=True))
        form_overrides = dict(email=wtforms.EmailField)
        form_include_pk = True
    ```

## Export options

SQLAdmin supports exporting data in the list page. Currently only CSV export is supported.
The export options can be set per model and includes the following options:

* `can_export`: If the model can be exported. Default value is `True`.
* `column_export_list`: List of columns to include in the export data. Default is all model columns.
* `column_export_exclude_list`: List of columns to exclude in the export data.
* `export_max_rows`: Maximum number of rows to be exported. Default value is `0` which means unlimited.
* `export_types`: List of export types to be enabled. Default value is `["csv"]`.

## Templates

The template files are built using Jinja2 and can be completely overridden in the configurations.
The pages available are:

* `list_template`: Template to use for models list page. Default is `list.html`.
* `create_template`: Template to use for model creation page. Default is `create.html`.
* `details_template`: Template to use for model details page. Default is `details.html`.
* `edit_template`: Template to use for model edit page. Default is `edit.html`.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        list_template = "custom_list.html"
    ```

For more information about working with template see [Working with Templates](./working_with_templates.md).

## Custom Views

To add custom views to the Admin interface, you can use the `BaseView` included in SQLAdmin.

For example:

!!! example

    ```python
    from sqladmin import BaseView, expose

    class CustomView(BaseView):
        name = "Custom Page"
        icon = "fa-chart-line"

        @expose("/custom", methods=["GET"])
        def custom_page(self, request):
            return self.templates.TemplateResponse(
                "custom.html",
                context={"request": request},
            )

    admin.add_view(CustomView)
    ```

This will assume a `templates` directory created in your project.
You can modify this when you create an Admin instance:

```python
from sqladmin import Admin

admin = Admin(templates_dir="my_templates", ...)
```
