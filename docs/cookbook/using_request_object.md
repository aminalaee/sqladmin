If you want to access the `request` object for the admin,
doing actions like create/update/delete you can override the specific `ModelView` methods.

These methods include:

- `insert_model(request, data)`
- `update_model(request, pk, data)`
- `delete_model(request, pk)`

A common use case is to access the `request.user` and store that in create/update model:

```python
class User(Base):
    __tablename__ = "user"

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String)


class Post(Base):
    __tablename__ = "post"

    id = mapped_column(Integer, primary_key=True)
    text = mapped_column(String)
    author = relationship("User")
    author_id = mapped_column(Integer, ForeignKey("user.id"), index=True)
```

And whenever a new `Post` is created we want to store the current admin user creating it.
This can be done by overriding the `insert_model` method:

```python
class PostAdmin(ModelView, model=Post):
    async def insert_model(self, request, data):
        data["user_id"] = request.user.id
        return await super().insert_model(request, data)
```

Here we've set the current `request.user.id` into the dictionary
of data which will create the `Post`.

The same thing can be done to control `update` and `delete` actions with the methods mentioned above.
