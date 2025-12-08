from starlette.requests import Request


def get_flashed_messages(request: Request):
    messages = []
    if "_messages" in request.session:
        messages = request.session.pop("_messages")

    return messages


def flash(
    request: Request, message: str, category: str = "primary", title: str = ""
) -> None:
    if "_messages" not in request.session:
        request.session["_messages"] = []

    request.session["_messages"].append(
        {
            "category": category,
            "title": title,
            "message": message,
        }
    )
