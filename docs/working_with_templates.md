The template uses `Jinja2` template engine and by default looks for a `templates` directory in your project.

If your `templates` directory has the default template files like `list.html` or `create.html` then they wiill be used.
Otherwise you can create custom templates and use them.

## Customizing templates

As the first step you should create a `templates` directory in you project.

Since `Jinja2` is modular, you can override your specific template file and do your changes.
For example you can create a `custom_details.html` file which overrides the `details.html` from
SQLAdmin and in the `content` block it adds custom HTML tags:

!!! example

    ```html name="custom_details.html"
    {% extends "details.html" %}
    {% block content %}
        {{ super() }}
        <p>Custom HTML</p>
    {% endblock %}
    ```

    ```python name="admin.py"
    class UserAdmin(ModelView, model=User):
        details_template = "custom_details.html"
    ```
