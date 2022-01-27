import anyio
from sqlalchemy import select
from starlette.authentication import (
    AuthCredentials, AuthenticationBackend, SimpleUser
)
from starlette.requests import HTTPConnection


from sqladmin.auth.models import User
from sqladmin.auth.utils.token import decode_access_token


class BasicAuthBackend(AuthenticationBackend):
    def __init__(self, session, _sync: bool):
        self.session = session
        self._sync = _sync

    async def authenticate(self, conn: HTTPConnection):
        access_token = conn.cookies.get("access_token")
        if access_token:
            try:
                data = decode_access_token(access_token)
                if self._sync:
                    res = await anyio.to_thread.run_sync(
                        self.session.execute,
                        select(User.username)
                            .where(User.username == username, User.is_active == True)  # noqa
                            .limit(1),
                    )
                else:
                    res = await self.session.execute(
                        select(User.username)
                            .where(User.username == username, User.is_active == True)  # noqa
                            .limit(1)
                    )
                if not res.scalar_one_or_none():
                    return
                return AuthCredentials(["authenticated"]), SimpleUser(data["username"])
            except:  # noqa
                pass
        return