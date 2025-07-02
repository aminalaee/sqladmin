SQLAdmin configuration options are heavily inspired by the Flask-Admin project.

This page will give you a basic introduction and for all the details
you can visit [API Reference](./api_reference/model_view.md).

Let's say you've defined your SQLAlchemy models like this:

```python
from sqlalchemy import Column, Boolean, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, relationship


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
    password = Column(String)
    address = relationship("Address", uselist=False, back_populates="user")

class Address(Base):
    __tablename__ = "address"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, primary_key=True)
    user = relationship("User", back_populates="address")
    street = Column(String)
    city = Column(String)
    state = Column(String)
    zip = Column(Integer)
    is_admin = Column(Boolean, default=False)


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

- `can_create`: If the model can create new instances via SQLAdmin. Default value is `True`.
- `can_edit`: If the model instances can be edited via SQLAdmin. Default value is `True`.
- `can_delete`: If the model instances can be deleted via SQLAdmin. Default value is `True`.
- `can_view_details`: If the model instance details can be viewed via SQLAdmin. Default value is `True`.
- `can_export`: If the model data can be exported in the list page. Default value is `True`.

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

- `name`: Display name for this model. Default value is the class name.
- `name_plural`: Display plural name for this model. Default value is class name + `s`.
- `icon`: Icon to be displayed for this model in the admin. Only FontAwesome and Tabler names are supported.
- `category`: Category name to display group of `ModelView` classes together in dropdown.
- `category_icon`: Category icon to display.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        name = "User"
        name_plural = "Users"
        icon = "fa-solid fa-user"
        category = "accounts"
        category_icon = "fa-solid fa-user"
    ```

## List page

These options allow configurations in the list page, in the case of this example
where you can view list of User records.

The options available are:

- `column_list`: List of columns or column names to be displayed in the list page.
- `column_exclude_list`: List of columns or column names to be excluded in the list page.
- `column_formatters`: Dictionary of column formatters in the list page.
- `column_searchable_list`: List of columns or column names to be searchable in the list page.
- `column_sortable_list`: List of columns or column names to be sortable in the list page.
- `column_default_sort`: Default sorting if no sorting is applied, tuple of (column, is_descending)
  or list of the tuple for multiple columns.
- `list_query`: A method with the signature of `(request) -> stmt` which can customize the list query.
- `count_query`: A method with the signature of `(request) -> stmt` which can customize the count query.
- `search_query`: A method with the signature of `(stmt, term) -> stmt` which can customize the search query.
- `column_filters`: A list of objects that implement the `ColumnFilter` protocol to be displayed in the list page. See example below.
- `details_query`: A method with the signature of `(request) -> stmt` which can customize the details query.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        column_list = [User.id, User.name, "address.zip_code"]
        column_searchable_list = [User.name]
        column_sortable_list = [User.id]
        column_formatters = {User.name: lambda m, a: m.name[:10]}
        column_default_sort = [(User.email, True), (User.name, False)]
        column_filterable_list = [User.is_admin]
    ```

!!! tip

    You can use the special keyword `"__all__"` in `column_list` or `column_details_list`
    if you don't want to specify all the columns manually. For example: `column_list = "__all__"`

### ColumnFilter
 
A ColumnFilter is a class that defines a filter for a column. A few standard filters are implemented in `sqladmin.filters` module. Here is an example of a generic ColumnFilter. Note that the fields `title`, `parameter_name`, `lookups` and `get_filtered_query` are required.

```python
class IsAdminFilter:
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = "Is Admin"

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "is_admin"

    def lookups(self, request, model) -> list[tuple[str, str]]:
        """
        Returns a list of tuples with the filter key and the human-readable label.
        """
        return [
            ("all", "All"),
            ("true", "Yes"),
            ("false", "No"),
        ]

    def get_filtered_query(self, query, value):
        """
        Returns a filtered query based on the filter value.
        """
        if value == "true":
            return query.filter(model.is_admin == True)
        elif value == "false":
            return query.filter(model.is_admin == False)
        else:
            return query
```

### Built in Column Filters

The following built in column filters are available. All filters have a default value of "all" which allows the user to not filter the column

* BooleanFilter - A filter for boolean columns, with the values of Yes (true) and No (false)
* AllUniqueStringValuesFilter - A filter for string columns, with the values of all unique values in the column
* StaticValuesFilter - A filter for string columns, with the values of a static list of values. This is similar to AllUniqueStringValuesFilter, but instead of getting the list of possible values from the database, you can provide a static list of values.
* ForeignKeyFilter - A filter for foreign key columns, with the values of all unique values in the foreign key column. To make this filter readable, you need to provide the field name from the foreign model that you want to display as the name of the filter.
  
Here is an example of how to use BooleanFilter, AllUniqueStringValuesFilter and ForeignKeyFilter:

```python

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    site_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sites.id"), nullable=True, default=None)
    site: Mapped[Optional["Site"]] = relationship(back_populates="users")

class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    users: Mapped[list["User"]] = relationship(back_populates="site")


# Define User Admin View
class UserAdmin(ModelView, model=User):
    column_list = ["id", "name", "email", "is_admin"]
    column_filters = [
        BooleanFilter(User.is_admin), 
        AllUniqueStringValuesFilter(User.name),
        ForeignKeyFilter(User.site_id, Site.name, title="Site")
    ]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    identity = "user"

```


## Details page

These options allow configurations in the details page, in the case of this example
where you can view details of a single User.

The options available are:

- `column_details_list`: List of columns or column names to be displayed in the details page.
- `column_details_exclude_list`: List of columns or column names to be excluded in the details page.
- `column_formatters_detail`: Dictionary of column formatters in the details page.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        column_details_list = [User.id, User.name, "address.zip_code"]
        column_formatters_detail = {User.name: lambda m, a: m.name[:10]}
    ```

!!! tip

    You can show related model's attributes by using a string value. For example
    "address.zip_code" will load the relationship but it will trigger extra queries for each
    relationship loading.

## Pagination options

The pagination options in the list page can be configured. The available options include:

- `page_size`: Default page size in pagination. Default is `10`.
- `page_size_options`: Pagination selector options. Default is `[10, 25, 50, 100]`.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        page_size = 50
        page_size_options = [25, 50, 100, 200]
    ```

## General options

There are a few options which apply to both List and Detail pages. They include:

- `column_labels`: A mapping of column labels, used to map column names to new names in all places.
- `column_type_formatters`: A mapping of type keys and callable values to format in all places.
  For example you can add custom date formatter to be used in both list and detail pages.
- `save_as`: A boolean to enable "save as new" option when editing an object.
- `save_as_continue`: A boolean to control the redirect URL if `save_as` is enabled.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        def date_format(value):
            return value.strftime("%d.%m.%Y")

        column_labels = {User.mail: "Email"}
        column_type_formatters = dict(ModelView.column_type_formatters, date=date_format)
        save_as = True
    ```

## Form options

SQLAdmin allows customizing how forms work with your models.
The forms are based on `WTForms` package and include the following options:

- `form`: Default form to be used for creating or editing the model. Default value is `None` and form is created dynamically.
- `form_base_class`: Default base class for creating forms. Default value is `wtforms.Form`.
- `form_args`: Dictionary of form field arguments supported by WTForms.
- `form_widget_args`: Dictionary of form widget rendering arguments supported by WTForms.
- `form_columns`: List of model columns to be included in the form. Default is all model columns.
- `form_excluded_columns`: List of model columns to be excluded from the form.
- `form_overrides`: Dictionary of form fields to override when creating the form.
- `form_include_pk`: Control if primary key column should be included in create/edit forms. Default is `False`.
- `form_ajax_refs`: Use Ajax with Select2 for loading relationship models async. This is use ful when the related model has a lot of records.
- `form_converter`: Allow adding custom converters to support additional column types.
- `form_edit_query`: A method with the signature of `(request) -> stmt` which can customize the edit form data.
- `form_rules`: List of form rules to manage rendering and behaviour of form.
- `form_create_rules`: List of form rules to manage rendering and behaviour of form in create page.
- `form_edit_rules`: List of form rules to manage rendering and behaviour of form in edit page.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        form_columns = [User.name]
        form_args = dict(name=dict(label="Full name"))
        form_widget_args = dict(email=dict(readonly=True))
        form_overrides = dict(email=wtforms.EmailField)
        form_include_pk = True
        form_ajax_refs = {
            "address": {
                "fields": ("zip_code", "street"),
                "order_by": ("id",),
            }
        }
        form_create_rules = ["name", "password"]
        form_edit_rules = ["name"]
    ```

### Related models

To define how related model is displayed in the dropdown, `__str__` method must be difined in the related model.

## Export options

SQLAdmin supports exporting data in the list page. Currently only CSV export is supported.
The export options can be set per model and includes the following options:

- `can_export`: If the model can be exported. Default value is `True`.
- `column_export_list`: List of columns to include in the export data. Default is all model columns.
- `column_export_exclude_list`: List of columns to exclude in the export data.
- `export_max_rows`: Maximum number of rows to be exported. Default value is `0` which means unlimited.
- `export_types`: List of export types to be enabled. Default value is `["csv","json"]`.

## Templates

The template files are built using Jinja2 and can be completely overridden in the configurations.
The pages available are:

- `list_template`: Template to use for models list page. Default is `sqladmin/list.html`.
- `create_template`: Template to use for model creation page. Default is `sqladmin/create.html`.
- `details_template`: Template to use for model details page. Default is `sqladmin/details.html`.
- `edit_template`: Template to use for model edit page. Default is `sqladmin/edit.html`.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        list_template = "custom_list.html"
    ```

For more information about working with template see [Working with Templates](./working_with_templates.md).

## Template configurations

The following options are available to configure the templates:

* `show_compact_lists`: If `False`, the list of objects will be displayed in a separate line for each object. Default is `True`.

## Events

There might be some cases which you want to do some actions
before or after a model was created, updated or deleted.

There are four methods you can override to achieve this:

- `on_model_change`: Called before a model was created or updated.
- `after_model_change`: Called after a model was created or updated.
- `on_model_delete`: Called before a model was deleted.
- `after_model_delete`: Called after a model was deleted.

By default these methods do nothing.

!!! example

    ```python
    class UserAdmin(ModelView, model=User):
        async def on_model_change(self, data, model, is_created, request):
            # Perform some other action
            ...

        async def on_model_delete(self, model, request):
            # Perform some other action
            ...
    ```

## Custom Action

To add custom action on models to the Admin, you can use the `action` decorator.

!!! example

    ```python
    from sqladmin import BaseView, action

    class UserAdmin(ModelView, model=User):
        @action(
            name="approve_users",
            label="Approve",
            confirmation_message="Are you sure?",
            add_in_detail=True,
            add_in_list=True,
        )
        async def approve_users(self, request: Request):
            pks = request.query_params.get("pks", "").split(",")
            if pks:
                for pk in pks:
                    model: User = await self.get_object_for_edit(pk)
                    ...

            referer = request.headers.get("Referer")
            if referer:
                return RedirectResponse(referer)
            else:
                return RedirectResponse(request.url_for("admin:list", identity=self.identity))

    admin.add_view(UserAdmin)
    ```

The available options for `action` are:

- `name`: A string name to be used in URL for this action.
- `label`: A string for describing this action.
- `add_in_list`: A boolean indicating if this action should be available in list page.
- `add_in_detail`: A boolean indicating if this action should be available in detail page.
- `confirmation_message`: A string message that if defined, will open a modal to ask for confirmation before calling the action method.
