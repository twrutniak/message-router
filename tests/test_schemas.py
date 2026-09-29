import pytest
from pydantic import ValidationError

from app.schemas import RouteRequest, RouteResponse
from app.settings import settings


def test_valid_request_strips_message():
    request = RouteRequest(email="jan.nowak@example.com", message="  Nie działa komputer \n")
    assert request.message == "Nie działa komputer"


@pytest.mark.parametrize(
    "email", ["", "nie-email", "jan@", "@example.com", "jan nowak@example.com"]
)
def test_invalid_email_rejected(email):
    with pytest.raises(ValidationError):
        RouteRequest(email=email, message="Cześć")


@pytest.mark.parametrize("message", ["", "   ", "\n\t"])
def test_empty_message_rejected(message):
    with pytest.raises(ValidationError):
        RouteRequest(email="jan.nowak@example.com", message=message)


def test_message_length_limit():
    RouteRequest(email="jan.nowak@example.com", message="x" * settings.message_max_length)
    with pytest.raises(ValidationError):
        RouteRequest(email="jan.nowak@example.com", message="x" * (settings.message_max_length + 1))


def test_response_status_restricted():
    RouteResponse(status="sent", routed_to="it@example.com", subject="Temat")
    with pytest.raises(ValidationError):
        RouteResponse(status="ok", routed_to="it@example.com", subject="Temat")
