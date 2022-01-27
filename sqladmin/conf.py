from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    DEBUG: bool = True
    DATABASE_URL: str  # db connect url

    @validator("DEBUG", pre=True)
    def get_debug(cls, v: str) -> bool:
        if isinstance(v, str):
            if v != "True":
                return False
        return True

    # sentry's config

    # SENTRY_DSN: Optional[HttpUrl] = None
    # SENTRY_ENVIROMENT: str = "development"
    #
    # @validator("SENTRY_DSN", pre=True)
    # def sentry_dsn_can_be_blank(cls, v: str) -> Optional[str]:
    #     if v and len(v) > 0:
    #         return v
    #     return None

    class Config:
        case_sensitive = True
        env_file = ".env"  # default env file

    # init sentry
    # def __init__(self):
    #     super(Settings, self).__init__()
    #
    #     if self.SENTRY_DSN:
    #         import sentry_sdk
    #
    #         sentry_sdk.init(
    #             dsn=self.SENTRY_DSN,
    #             environment=self.SENTRY_ENVIROMENT,
    #         )


settings = Settings()
