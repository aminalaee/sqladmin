class SQLAdminException(Exception):
    pass


class InvalidModelError(SQLAdminException):
    pass


class InvalidColumnError(SQLAdminException):
    pass


class NoConverterFound(SQLAdminException):
    pass
