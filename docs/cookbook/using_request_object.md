If you want to access the `request` object for the admin,
doing actions like create/update/delete you can override the specific `ModelView` methods.

These methods include:

- `insert_model(request, data)`
- `update_model(request, pk, data)`
- `delete_model(request, pk)`

