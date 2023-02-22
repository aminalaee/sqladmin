# Working with Files and Images

You can use the [sqlalchemy-fields](https://github.com/aminalaee/sqlalchemy-fields) package
which provides some extra fields to use with or without `SQLAdmin`.

Some of the fields included in `sqlalchemy-fields` are:

- `EmailType`
- `FileType`
- `ImageType`
- `IPAddressType`
- `URLType`
- `UUIDType`

So here we have custom `FileType` and `ImageType` which work out of the box with `SQLAdmin`.

In addition to that, `sqlalchemy-fields` provides different storages for the file types:

- `FileSystemStorage` for storing files in local file system.
- `S3Storage` for storing files in Amazon S3 or S3-compatible storages.

Let's do a minimal example:

```python
from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy_fields.storages import FileSystemStorage
from sqlalchemy_fields.types import FileType, IPAddressType


Base = declarative_base()
engine = create_engine("sqlite:///example.db")
app = FastAPI()
admin = Admin(app, engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)    
    file = Column(FileType(storage=FileSystemStorage(path="/tmp")))
    ip = Column(IPAddressType)


class UserAdmin(ModelView, model=User):
    column_list = [User.id]


admin.add_view(UserAdmin)
```

Now visiting `/admin/user` to create a new User,
there's an HTML file field to upload files form local.

The `FileSystemStorage` is configured to store files in the `/tmp` directory of your local.

Custom types are not limited to `SQLAdmin`, you can for example query User objects with:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

with Session(engine) as session:
    stmt = select(User).limit(1)
    result = session.execute(stmt)
    user = result.scalars().one()
    print(file, type(file))

"""
/tmp/example.txt, sqlalchemy_fields.storages.StorageFile
"""
```

So the following return types are available from custom types:

- `StorageFile` -> Returned from `FileType` columns and has file-related properties like name, path, size, etc.
- `StorageImage` -> Returned from `ImageType` which is the same as `FileType` except it includes Image height and width properties.

For complete features and API reference of the `sqlalchemy-fields` you can visit the docs at [https://aminalaee.dev/sqlalchemy-fields](https://aminalaee.dev/sqlalchemy-fields).
