"""The gateway's sign-in address helpers."""

from app.infra import gateway_signin


def test_signin_url_is_the_https_address_with_the_token():
    assert gateway_signin.signin_url("10.0.0.5", 8080, "tok") == "https://10.0.0.5:8080/?token=tok"


def test_display_url_never_contains_the_token():
    shown = gateway_signin.display_url("10.0.0.5", 8080)
    assert shown == "https://10.0.0.5:8080"
    assert "token" not in shown and "?" not in shown
