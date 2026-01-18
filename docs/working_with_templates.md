The template uses `Jinja2` template engine and by default looks for a `templates/sqladmin` directory in your project.

If your `templates/sqladmin` directory has the default template files like `list.html` or `create.html` then they will be used.
Otherwise you can create custom templates and use them.

## Customizing templates

As the first step you should create a `templates/sqladmin` directory in you project.

Since `Jinja2` is modular, you can override your specific template file and do your changes.
For example you can create a `custom_details.html` file which overrides the `details.html` from
SQLAdmin and in the `content` block it adds custom HTML tags:

!!! example

    ```html title="custom_details.html"
    {% extends "sqladmin/details.html" %}
    {% block content %}
        {{ super() }}
        <p>Custom HTML</p>
    {% endblock %}
    ```

    ```python title="admin.py"
    class UserAdmin(ModelView, model=User):
        details_template = "sqladmin/custom_details.html"
    ```

## Overriding default templates

If you need to change one of the existing default templates in SQLAdmin such that it affects multiple pages, you can do so by copying the existing template from `templates/sqladmin` into your `templates/sqladmin` directory. It will then be used instead of the one in the package. For example if there is some Javascript you want to run on every page you may want to do it in layout.html like so:

!!! example

    ```html title="myproject/templates/sqladmin/layout.html"
    ...
    </div>
    </div>
    {% endblock %}

    {% block tail %}
    <script type="text/javascript">
        console.log('hello world');
    </script>
    {% endblock %}

    ```

## Customizing Jinja2 environment

You can add custom environment options to use it on your custom templates. First set up a project:

```python
from sqladmin import Admin
from starlette.applications import Starlette


app = Starlette()
admin = Admin(app, engine)
```

Then you can add your environment options:

### Adding filters

```python
def datetime_format(value, format="%H:%M %d-%m-%y"):
    return value.strftime(format)

admin.templates.env.filters["datetime_format"] = datetime_format
```

Usage in templates:

```
{{ article.pub_date|datetimeformat }}
{{ article.pub_date|datetimeformat("%B %Y") }}
```

### Adding tests

```python
import math

def is_prime(n):
    if n == 2:
        return True

    for i in range(2, int(math.ceil(math.sqrt(n))) + 1):
        if n % i == 0:
            return False

    return True

admin.templates.env.tests["prime"] = is_prime
```

Usage in templates:

```
{% if value is prime %}
    {{ value }} is a prime number
{% else %}
    {{ value }} is not a prime number
{% endif %}
```

# Adding globals

```python
def value_is_filepath(value: Any) -> bool:
    return isinstance(value, str) and os.path.isfile(value)

admin.templates.env.globals["value_is_filepath"] = value_is_filepath
```

Usage in templates:

```
{% if value_is_filepath(value) %}
    {{ value }} is file path
{% else %}
    {{ value }} is not file path
{% endif %}
```

# Template Blocks
The SQLAdmin templates use blocks to allow easy customization and extension of the templates. Here is a list of the main blocks available SQLAdmin templates:

| Block Name | Description |
|------------|-------------|
| `head_meta`  | Page metadata in the header |
| `head_css`    | Various CSS includes in the header |
| `head`     | Empty block in HTML head, in case you want to put something there |
| `head_tail`  | Additional HTML elements before the closing `</head>` tag |
| `body`     | The main body of the page |
| `main`     | The main container for the page content |
| `content`  | The main content area where page-specific content is rendered |
| `tail`     | Additional HTML elements before the closing `</body>` tag |
| `tail_js `  | Various JavaScript includes before the closing `</body>` tag |
| `create_form` | The form used in the create view containing fields |
| `edit_form` | The form used in the edit view containing fields |
| `details_view` | The details view div containing the the record's table |
| `submit_buttons_bottom` | The submit buttons at the bottom of create/edit views |
| `action_buttons_bottom` | The action buttons at the bottom of details view |
| `model_list_table` | The table displaying records in the list view |
| `model_menu_bar` | The menu bar at the top of model list view |


You can override these blocks in your custom templates to modify the layout and appearance of the admin interface as needed.
