The template uses `Jinja2` template engine and by default looks for a `templates` directory in your project.

If your `templates` directory has the default template files like `sqladmin/list.html` or `sqladmin/create.html` then they will be used.
Otherwise you can create custom templates and use them.

## Customizing templates

As the first step you should create a `templates` directory in you project.

Since `Jinja2` is modular, you can override your specific template file and do your changes.
For example you can create a `custom_details.html` file which overrides the `sqladmin/details.html` from
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
        details_template = "custom_details.html"
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
