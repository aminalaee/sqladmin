import functools
from typing import Any, Callable

from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse


class AuthenticationBackend:
    """Base class for implementing the Authentication into SQLAdmin.
    You need to inherit this class and override the methods:
    `login`, `logout` and `authenticate`.
    """

    def __init__(self, secret_key: str) -> None:
        self.middlewares = [
            Middleware(SessionMiddleware, secret_key=secret_key),
        ]

    async def login(self, request: Request) -> bool:
        """Implement login logic here.
        You can access the login form data `await request.form()`
        andvalidate the credentials.
        """
        raise NotImplementedError()

    async def logout(self, request: Request) -> bool:
        """Implement logout logic here.
        This will usually clear the session with `request.session.clear()`.
        """
        raise NotImplementedError()

    async def authenticate(self, request: Request) -> bool:
        """Implement authenticate logic here.
        This method will be called for each incoming request
        to validate the authentication.
        """
        raise NotImplementedError()


def login_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to check authentication of Admin routes.
    If no authentication backend is setup, this will do nothing.
    """

    @functools.wraps(func)
    async def wrapper_decorator(*args: Any, **kwargs: Any) -> Any:
        admin, request = args[0], args[1]
        auth_backend = admin.authentication_backend
        if auth_backend is not None:
            is_authenticated = await auth_backend.authenticate(request)
            if not is_authenticated:
                return RedirectResponse(request.url_for("admin:login"), status_code=302)

        return await func(*args, **kwargs)

    return wrapper_decorator
