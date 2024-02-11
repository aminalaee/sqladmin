from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from starlette.requests import Request

from sqladmin import ModelView
from sqladmin._menu import CategoryMenu, ItemMenu, Menu, ViewMenu

Base = declarative_base()  # type: ignore


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)


class UserAdmin(ModelView, model=User):
    ...


class InvisibleUserAdmin(ModelView, model=User):
    def is_visible(self, request: Request) -> bool:
        return False


class InaccessibleUserAdmin(ModelView, model=User):
    def is_accessible(self, request: Request) -> bool:
        return False


REQUEST = Request({"type": "http"})


def test_item_menu():
    item_menu = ItemMenu(name="item")
    child_menu = ItemMenu(name="child")
    item_menu.add_child(child_menu)

    assert item_menu.display_name == "item"
    assert item_menu.url(REQUEST) == "#"
    assert item_menu.is_visible(REQUEST) is True
    assert item_menu.is_accessible(REQUEST) is True
    assert item_menu.is_active(REQUEST) is False
    assert item_menu.type_ == "ItemMenu"


def test_category_menu():
    item_menu = CategoryMenu(name="category")

    assert item_menu.is_active(REQUEST) is False
    assert item_menu.type_ == "Category"


def test_invisible_category_menu():
    category_menu = CategoryMenu(name="category")
    first_child = ViewMenu(view=InvisibleUserAdmin(), name="view1")
    category_menu.add_child(first_child)

    assert first_child.is_visible(REQUEST) is False
    assert category_menu.is_visible(REQUEST) is False

    second_child = ViewMenu(view=UserAdmin(), name="view2")
    category_menu.add_child(second_child)

    assert second_child.is_visible(REQUEST) is True
    assert category_menu.is_visible(REQUEST) is True


def test_inaccessible_category_menu():
    category_menu = CategoryMenu(name="category")
    first_child = ViewMenu(view=InaccessibleUserAdmin(), name="view1")
    category_menu.add_child(first_child)

    assert first_child.is_accessible(REQUEST) is False
    assert category_menu.is_accessible(REQUEST) is False

    second_child = ViewMenu(view=UserAdmin(), name="view2")
    category_menu.add_child(second_child)

    assert second_child.is_accessible(REQUEST) is True
    assert category_menu.is_accessible(REQUEST) is True


def test_view_menu():
    item_menu = ViewMenu(view=UserAdmin(), name="view")

    assert item_menu.display_name == "Users"
    assert item_menu.type_ == "View"
    assert item_menu.is_visible(REQUEST) is True
    assert item_menu.is_accessible(REQUEST) is True
    assert item_menu.is_active(REQUEST) is False


def test_menu():
    item_menu = ItemMenu(name="item")
    child_menu = ItemMenu(name="child")
    item_menu.add_child(child_menu)

    menu = Menu()
    menu.add(item_menu)

    item_menu = ItemMenu(name="item")
    another_child = ItemMenu(name="another_child")
    item_menu.add_child(another_child)

    menu.add(item_menu)

    assert len(menu.items) == 1
    assert len(menu.items.pop().children) == 2
