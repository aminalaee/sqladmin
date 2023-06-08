import functools
import inspect
from typing import Any, Callable, Optional

from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import Response


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

    async def authenticate(self, request: Request) -> Optional[Response]:
        """Implement authenticate logic here.
        This method will be called for each incoming request
        to validate the authentication.

        If the request is authenticated, this method should return `None` or do nothing.
        Otherwise it should return a `Response` object,
        like a redirect to the login page or SSO page.
        """
        raise NotImplementedError()


def login_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to check authentication of Admin routes.
    If no authentication backend is setup, this will do nothing.
    """

    @functools.wraps(func)
    async def wrapper_decorator(*args: Any, **kwargs: Any) -> Any:
        admin, request = args[0], args[1]
        auth_backend = getattr(admin, "authentication_backend", None)
        if auth_backend is not None:
            response = await auth_backend.authenticate(request)
            if response and isinstance(response, Response):
                return response

        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper_decorator
