import typer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sqladmin.auth.models import User
from sqladmin.conf import settings

app = typer.Typer()


@app.command()
def createmanager(username: str, password: str):
    """
    create manager
    """
    engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
    user = User(
        username=username, is_active=True
    )
    user.set_password(password)
    session = Session(engine)
    session.add(user)
    session.commit()
    print(f"create {username} success.")


def main():
    app()


if __name__ == "__main__":
    main()
