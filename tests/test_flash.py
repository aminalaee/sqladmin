import pytest
from starlette.requests import Request

from sqladmin.flash import flash, get_flashed_messages


@pytest.fixture
def mock_request_with_session():
    mock_scope = {"session": {}, "type": "http"}
    request = Request(scope=mock_scope)

    return request


@pytest.fixture
def mock_request_without_session():
    mock_scope = {"type": "http"}
    request = Request(scope=mock_scope)

    return request


def test_flash_success_with_defaults(mock_request_with_session):
    request = mock_request_with_session

    result = flash(request, message="Test message")

    assert result is True

    messages = request.session.get("_messages")
    assert len(messages) == 1
    assert messages[0]["message"] == "Test message"
    assert messages[0]["category"] == "primary"  # Default category
    assert messages[0]["title"] == ""  # Default title


def test_flash_success_with_custom_values(mock_request_with_session):
    request = mock_request_with_session

    result = flash(request, message="Custom message", category="danger", title="Error")

    assert result is True

    messages = request.session.get("_messages")
    assert len(messages) == 1
    assert messages[0]["message"] == "Custom message"
    assert messages[0]["category"] == "danger"
    assert messages[0]["title"] == "Error"


def test_flash_multiple_messages(mock_request_with_session):
    request = mock_request_with_session

    flash(request, message="First message")
    flash(request, message="Second message", category="success")

    messages = request.session.get("_messages")
    assert len(messages) == 2
    assert messages[1]["category"] == "success"


def test_flash_no_session_middleware(mock_request_without_session):
    request = mock_request_without_session

    result = flash(request, message="Should fail")

    assert result is False

    assert "session" not in request.scope


def test_get_flashed_messages_no_session_middleware(mock_request_without_session):
    request = mock_request_without_session

    messages = get_flashed_messages(request)

    assert messages == []
    assert isinstance(messages, list)


def test_get_flashed_messages_empty_session(mock_request_with_session):
    request = mock_request_with_session

    messages = get_flashed_messages(request)

    assert messages == []
    assert "_messages" not in request.session


def test_get_flashed_messages_retrieval_and_pop(mock_request_with_session):
    request = mock_request_with_session

    initial_messages = [
        {"category": "info", "title": "", "message": "Message 1"},
        {"category": "warning", "title": "Alert", "message": "Message 2"},
    ]
    request.session["_messages"] = initial_messages

    retrieved_messages = get_flashed_messages(request)

    assert len(retrieved_messages) == 2
    assert retrieved_messages[0]["message"] == "Message 1"
    assert retrieved_messages[1]["category"] == "warning"

    assert "_messages" not in request.session


def test_get_flashed_messages_idempotency(mock_request_with_session):
    request = mock_request_with_session

    request.session["_messages"] = [{"message": "Only once"}]
    first_retrieval = get_flashed_messages(request)

    second_retrieval = get_flashed_messages(request)

    assert len(first_retrieval) == 1
    assert second_retrieval == []
    assert "_messages" not in request.session
