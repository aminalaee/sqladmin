from collections.abc import Generator

import pytest
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import Session, declarative_base
from starlette.applications import Starlette
from starlette.testclient import TestClient
from wtforms.validators import DataRequired

from sqladmin import Admin, Fieldset, ModelView
from sqladmin.exceptions import InvalidModelError
from tests.common import sync_engine as engine

Base = declarative_base()  # type: ignore


class User(Base):
    __tablename__ = "fieldset_users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    is_admin = Column(Boolean)
    note = Column(String)
    data = Column(String)  # collides with WTForms' own `data` attribute


@pytest.fixture(autouse=True, scope="module")
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def render(view: type[ModelView], page: str = "create") -> str:
    app = Starlette()
    admin = Admin(app=app, engine=engine)
    admin.add_view(view)
    with TestClient(app=app, base_url="http://testserver") as client:
        response = client.get(f"/admin/{view.identity}/{page}")
        assert response.status_code == 200, response.status_code
        return response.text


class GroupedUserAdmin(ModelView, model=User):
    form_fieldsets = [
        Fieldset(None, [User.name, User.email]),
        Fieldset(
            "Permissions",
            [User.is_admin, User.data],
            description="What this user is allowed to reach.",
            collapsed=True,
        ),
    ]


def test_fieldset_renders_title_and_description() -> None:
    html = render(GroupedUserAdmin)

    assert '<h4 class="mb-0">Permissions</h4>' in html
    assert "What this user is allowed to reach." in html


def test_collapsed_fieldset_uses_bootstrap_collapse() -> None:
    html = render(GroupedUserAdmin)

    assert 'data-bs-toggle="collapse"' in html
    assert 'href="#form-fieldset-1"' in html
    assert 'id="form-fieldset-1"' in html


def test_fieldsets_control_field_order() -> None:
    html = render(GroupedUserAdmin)

    positions = [
        html.index(f'name="{name}"')
        for name in ("name", "email", "is_admin", "data", "note")
    ]
    assert positions == sorted(positions)


def test_field_in_no_fieldset_renders_last_and_ungrouped() -> None:
    # `note` is in no fieldset. It must still render, after the declared
    # groups, so adding a column never silently drops it from the form.
    html = render(GroupedUserAdmin)

    assert 'name="note"' in html
    assert html.index('name="note"') > html.index('id="form-fieldset-1"')
    assert 'id="form-fieldset-2"' not in html


def test_wtforms_renamed_field_can_be_grouped() -> None:
    # `data` is renamed to `data_` on the form class but keeps its rendered
    # name, so a fieldset naming the column still has to match it.
    html = render(GroupedUserAdmin)

    assert html.index('name="is_admin"') < html.index('name="data"')
    assert html.index('name="data"') < html.index('name="note"')


def test_without_fieldsets_markup_is_unchanged() -> None:
    class PlainUserAdmin(ModelView, model=User):
        pass

    html = render(PlainUserAdmin)

    assert "sqladmin-fieldset" not in html
    assert 'name="note"' in html


def test_same_fieldsets_apply_to_the_edit_page() -> None:
    with Session(engine) as session:
        session.add(User(id=1, name="Bob"))
        session.commit()

    html = render(GroupedUserAdmin, page="edit/1")

    assert '<h4 class="mb-0">Permissions</h4>' in html
    assert html.index('name="name"') < html.index('name="note"')


def test_unknown_field_name_raises() -> None:
    class TypoUserAdmin(ModelView, model=User):
        form_fieldsets = [Fieldset("Oops", ["naem"])]

    with pytest.raises(InvalidModelError, match="naem"):
        render(TypoUserAdmin)


def test_field_in_two_fieldsets_raises() -> None:
    class DuplicateUserAdmin(ModelView, model=User):
        form_fieldsets = [
            Fieldset("A", [User.name]),
            Fieldset("B", [User.name]),
        ]

    with pytest.raises(InvalidModelError, match="more than one fieldset"):
        render(DuplicateUserAdmin)


class DjangoStyleUserAdmin(ModelView, model=User):
    # Django's `(title, options)` tuples, so a ModelAdmin declaration can be
    # pasted across unchanged.
    form_fieldsets = [
        (None, {"fields": [User.name, User.email]}),
        (
            "Permissions",
            {
                "fields": [User.is_admin, User.data],
                "description": "What this user is allowed to reach.",
                "classes": ["collapse", "border-top"],
            },
        ),
    ]


def test_django_style_tuples_are_accepted() -> None:
    html = render(DjangoStyleUserAdmin)

    assert '<h4 class="mb-0">Permissions</h4>' in html
    assert "What this user is allowed to reach." in html
    assert 'name="note"' in html


def test_collapse_class_implies_collapsed() -> None:
    html = render(DjangoStyleUserAdmin)

    assert 'data-bs-toggle="collapse"' in html
    assert 'id="form-fieldset-1"' in html


def test_extra_classes_reach_the_wrapper_but_collapse_does_not() -> None:
    # `collapse` is consumed by the collapsed behaviour; leaving it on the
    # wrapper would hide the heading along with the body.
    html = render(DjangoStyleUserAdmin)

    assert 'class="mb-4 sqladmin-fieldset border-top"' in html


def test_malformed_fieldset_entry_raises() -> None:
    class BrokenUserAdmin(ModelView, model=User):
        form_fieldsets = ["not-a-fieldset"]  # type: ignore[list-item]

    with pytest.raises(InvalidModelError, match="Fieldset"):
        render(BrokenUserAdmin)


def test_collapsed_fieldset_stays_closed_without_errors() -> None:
    html = render(DjangoStyleUserAdmin)

    assert 'id="form-fieldset-1"' in html
    assert 'class="collapse"' in html
    assert "collapse show" not in html


def test_collapsed_fieldset_opens_when_it_holds_a_validation_error() -> None:
    # Otherwise the "this field is required" message is hidden inside a closed
    # section and the form looks like it failed for no reason.
    class ValidatedUserAdmin(ModelView, model=User):
        form_args = {"email": {"validators": [DataRequired()]}}
        form_fieldsets = [
            (None, {"fields": [User.name]}),
            ("Contact", {"fields": [User.email], "classes": ["collapse"]}),
        ]

    app = Starlette()
    admin = Admin(app=app, engine=engine)
    admin.add_view(ValidatedUserAdmin)

    with TestClient(app=app, base_url="http://testserver") as client:
        response = client.post(
            f"/admin/{ValidatedUserAdmin.identity}/create",
            data={"name": "Bob", "email": ""},
        )

    assert response.status_code == 400
    assert "collapse show" in response.text
    assert 'aria-expanded="true"' in response.text
