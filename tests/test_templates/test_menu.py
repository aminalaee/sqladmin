from pathlib import Path

import jinja2
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from starlette.requests import Request

from sqladmin import ModelView
from sqladmin._menu import CategoryMenu, Menu, ViewMenu

Base = declarative_base()  # type: ignore


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)


class UserAdmin(ModelView, model=User):
    def is_visible(self, request: Request) -> bool:
        return request.scope.get('show_hidden', False)

    def is_accessible(self, request: Request) -> bool:
        return request.scope.get('show_hidden', False)


def clear_whitespace(input_str: str) -> str:
    return ' '.join(input_str.split())


def test_category_menu_without_access(
    jinja_env: jinja2.Environment,
    macros_content: str,
    request_without_access: Request,
    resources_path: Path,
):
    category_menu = CategoryMenu(name='category')
    child_item = ViewMenu(view=UserAdmin(), name='view')
    category_menu.add_child(child_item)

    assert child_item.is_visible(request_without_access) is False
    assert category_menu.is_visible(request_without_access) is False

    menu = Menu()
    menu.add(category_menu)

    tpl = jinja_env.from_string(macros_content + '{{ display_menu(menu, request) }}')
    render = tpl.render(menu=menu, request=request_without_access)
    expected = (resources_path / 'empty-menu.html').read_text()
    assert clear_whitespace(render) == clear_whitespace(expected)


def test_category_menu_with_access(
    jinja_env: jinja2.Environment,
    macros_content: str,
    request_with_access: Request,
    resources_path: Path,
):
    category_menu = CategoryMenu(name='category')
    child_item = ViewMenu(view=UserAdmin(), name='view')
    category_menu.add_child(child_item)

    assert child_item.is_visible(request_with_access) is True
    assert category_menu.is_visible(request_with_access) is True

    menu = Menu()
    menu.add(category_menu)

    tpl = jinja_env.from_string(macros_content + '{{ display_menu(menu, request) }}')
    render = tpl.render(menu=menu, request=request_with_access)
    expected = (resources_path / 'menu-with-one-category.html').read_text()
    assert clear_whitespace(render) == clear_whitespace(expected)
