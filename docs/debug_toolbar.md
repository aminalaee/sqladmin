```markdown
# Debugging with Debug Toolbar

SQLAdmin works with any ASGI-compatible debug toolbar.  
The recommended one is the async-native [`debug-toolbar`](https://github.com/JacobCoffee/debug-toolbar).

This guide shows how to enable it with FastAPI (the most common case).

## Installation

```bash
pip install "debug-toolbar[fastapi]"
```

If you also want the SQLAlchemy panel (recommended):

```bash
pip install "debug-toolbar[fastapi,advanced-alchemy]"
```

## Basic Usage

```python
from fastapi import FastAPI
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base
from sqladmin import Admin, ModelView
from debug_toolbar.fastapi import FastAPIDebugToolbarConfig, setup_debug_toolbar

Base = declarative_base()
engine = create_engine(
    "sqlite:///example.db",
    connect_args={"check_same_thread": False},
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)

Base.metadata.create_all(engine)

app = FastAPI()
admin = Admin(app, engine)

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.name]

admin.add_view(UserAdmin)

# Enable debug toolbar
config = FastAPIDebugToolbarConfig(enabled=True)
setup_debug_toolbar(app, config)
```

After starting the server, open any page (including `/admin`) and you will see the toolbar.

## Recommended Panels

```python
config = FastAPIDebugToolbarConfig(
    enabled=True,
    extra_panels=[
        "debug_toolbar.extras.advanced_alchemy.SQLAlchemyPanel",
        "debug_toolbar.core.panels.headers.HeadersPanel",
        "debug_toolbar.core.panels.settings.SettingsPanel",
        "debug_toolbar.core.panels.templates.TemplatesPanel",
        "debug_toolbar.core.panels.profiling.ProfilingPanel",
        "debug_toolbar.core.panels.alerts.AlertsPanel",
        "debug_toolbar.core.panels.memory.MemoryPanel",
        "debug_toolbar.core.panels.cache.CachePanel",
    ],
)

setup_debug_toolbar(app, config)
```

The most useful panel for SQLAdmin is **SQLAlchemyPanel** — it shows every SQL query executed by the admin interface, including N+1 detection.
```