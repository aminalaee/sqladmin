There are different approaches when it comes to working with templates in SQLAdmin.
You can simply replace a template file and implement it yourself,
or you could customize parts of the template without implementing the whole page.

## Replacing templates

You can create a directory called `templates` in your project
and create relevant template files in it.

If you name your files the same way SQLAdmin does, for example `list.html` or `details.html`
then you don't have to do anything else. They will be picked up by SQLAdmin automatically.

But if you name the files something else,
then you need to specify the name in your ModelAdmin classes.

!!! example

    ```python
    class UserAdmin(ModelAdmin, model=User):
        details_template = "details.html"
        list_template = "custom_list.html"
    ```

## Customizing templates
