from typing import Optional

from fastapi_users.authentication import (
    AuthenticationBackend,
    Transport, Strategy
)
from fastapi import HTTPException, status
from fastapi.security import APIKeyCookie, OAuth2PasswordRequestForm
from fastapi_users.manager import UserManagerDependency
from fastapi_users.router import ErrorCode
from fastapi_users.types import DependencyCallable
from fastapi_users.authentication import Authenticator
from fastapi_users import models
from starlette.requests import Request
from starlette.responses import RedirectResponse
import sqladmin.authentication


class SessionTransport(Transport):
    """
    Modified version of CookieTransport which simply reads cookies and returns tokens instead of full Responses
    """
    scheme: APIKeyCookie

    def __init__(self, name: str = 'fastapiusersauth'):
        super().__init__()
        self.scheme = APIKeyCookie(name=name, auto_error=False)

    async def get_login_response(self, token: str) -> str:
        return token

    async def get_logout_response(self):
        pass

    @staticmethod
    def get_openapi_login_responses_success():
        return {}

    @staticmethod
    def get_openapi_logout_responses_success():
        return {}


class FastapiUsersAuthenticationBackend(sqladmin.authentication.AuthenticationBackend):
    """
        Usage:

        from sqladmin import Admin
        from sqladmin.authentication_fastapi_users import FastapiUsersAuthenticationBackend
        admin = sqladmin.Admin(
            app,  # fastapi app/router
            engine,  # sqla engine
            authentication_backend=FastapiUsersAuthenticationBackend(secret_key='<SUPER SECRET KEY HERE>',
                                                                     # fast-users callables
                                                                     get_user_manager=get_user_manager,
                                                                     get_strategy=get_redis_strategy)
        )
    """
    def __init__(self, secret_key: str, get_user_manager: UserManagerDependency[models.UP, models.ID],
                 get_strategy: DependencyCallable[Strategy[models.UP, models.ID]], requires_verification: bool = False,
                 name: str = 'admin'):
        super().__init__(secret_key)
        self.get_user_manager = get_user_manager
        self.get_strategy = get_strategy
        self.backend = AuthenticationBackend(
            name=name,
            transport=SessionTransport(),
            get_strategy=get_strategy,
        )
        self.requires_verification = requires_verification
        self.authenticator = Authenticator([self.backend], self.get_user_manager)

    def _redirect_to_login(self, request: Request):
        return RedirectResponse(request.url_for("admin:login"), status_code=302)

    def _validate_user(self, user):
        # code adjusted from fastapi_users.router.auth.login
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
            )
        if self.requires_verification and not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.LOGIN_USER_NOT_VERIFIED,
            )
        if not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='LOGIN_USER_NOT_SUPERUSER',
            )

    async def authenticate(self, request: Request) -> Optional[RedirectResponse]:
        token = request.session.get("token")
        if not token:
            return self._redirect_to_login(request)

        kwargs = {
            'user_manager': self.get_user_manager(),
            f'strategy_{self.backend.name}': self.get_strategy(),
            self.backend.name: token
        }
        user = await self.authenticator.current_user(optional=True)(**kwargs)
        try:
            self._validate_user(user)
        except HTTPException:
            return self._redirect_to_login(request)

    async def login(self, request: Request) -> bool:
        form = await request.form()
        credentials = OAuth2PasswordRequestForm(scope='', username=form.get("username"), password=form.get("password"))

        user = await self.get_user_manager().authenticate(credentials)
        self._validate_user(user)

        token = await self.backend.login(self.get_strategy(), user)
        request.session["token"] = token
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True
