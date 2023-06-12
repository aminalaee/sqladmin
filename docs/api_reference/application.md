::: sqladmin.application.Admin
    handler: python
    options:
      members:
        - __init__

::: sqladmin.application.BaseAdmin
    handler: python
    options:
      members:
        - views
        - add_view
        - add_model_view
        - add_base_view

::: sqladmin.application.action
    handler: python
