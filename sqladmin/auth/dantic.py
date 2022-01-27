from pydantic import BaseModel


class LoginInfo(BaseModel):
    username: str
    password: str
