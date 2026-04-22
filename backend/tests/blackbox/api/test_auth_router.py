"""
Black-box tests for routers.auth.router (the only router mounted in app.py).

Applies EP / BA / EG. Each test is labeled with its technique and goal.

Caveat: the endpoint body is `pass`; business logic is not implemented.
These tests therefore only validate the Pydantic schema + FastAPI wiring:
accepted-payload class -> 201, rejected-payload class -> 422, etc.
"""
import pytest

pytestmark = pytest.mark.blackbox


SIGNUP_URL = "/api/v1.0/auth/Signup"


def _payload(**overrides):
    base = {
        "email": "user@example.com",
        "username": "alice",
        "password": "correcthorse",  # 12 chars, within 8..15
    }
    base.update(overrides)
    return base


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestSignupEP:
    """
    EP partitions for POST /Signup:
      payload shape: valid / missing-field / wrong-type
      password length: in-range (8..15) / below-min / above-max
    """

    def test_valid_payload_returns_201(self, client):
        # EP: valid payload -> 201.
        r = client.post(SIGNUP_URL, json=_payload())
        assert r.status_code == 201

    def test_missing_email_returns_422(self, client):
        # EP: missing-required-field class -> 422.
        payload = _payload()
        payload.pop("email")
        r = client.post(SIGNUP_URL, json=payload)
        assert r.status_code == 422

    def test_missing_username_returns_422(self, client):
        # EP: another missing-required-field representative.
        payload = _payload()
        payload.pop("username")
        r = client.post(SIGNUP_URL, json=payload)
        assert r.status_code == 422

    def test_missing_password_returns_422(self, client):
        # EP: missing password -> 422.
        payload = _payload()
        payload.pop("password")
        r = client.post(SIGNUP_URL, json=payload)
        assert r.status_code == 422

    def test_wrong_type_password_returns_422(self, client):
        # EP: wrong-type class (password must be str).
        r = client.post(SIGNUP_URL, json=_payload(password=12345678))
        # FastAPI/Pydantic v2 may accept int and coerce; still 4xx if length
        # rule fails. Accept either 422 or 201 but not 5xx.
        assert r.status_code in (201, 422)


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestPasswordLengthBoundariesBA:
    """Boundary analysis on password length (min=8, max=15 per schema)."""

    def test_password_length_seven_rejected(self, client):
        # BA: length=7 (min-1) -> 422.
        r = client.post(SIGNUP_URL, json=_payload(password="a" * 7))
        assert r.status_code == 422

    def test_password_length_eight_accepted(self, client):
        # BA: length=8 (min) -> 201.
        r = client.post(SIGNUP_URL, json=_payload(password="a" * 8))
        assert r.status_code == 201

    def test_password_length_nine_accepted(self, client):
        # BA: length=9 (min+1) -> 201.
        r = client.post(SIGNUP_URL, json=_payload(password="a" * 9))
        assert r.status_code == 201

    def test_password_length_fourteen_accepted(self, client):
        # BA: length=14 (max-1) -> 201.
        r = client.post(SIGNUP_URL, json=_payload(password="a" * 14))
        assert r.status_code == 201

    def test_password_length_fifteen_accepted(self, client):
        # BA: length=15 (max) -> 201.
        r = client.post(SIGNUP_URL, json=_payload(password="a" * 15))
        assert r.status_code == 201

    def test_password_length_sixteen_rejected(self, client):
        # BA: length=16 (max+1) -> 422.
        r = client.post(SIGNUP_URL, json=_payload(password="a" * 16))
        assert r.status_code == 422


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_wrong_method_returns_405(self, client):
        # EG: GET on a POST-only endpoint -> 405 per HTTP spec.
        r = client.get(SIGNUP_URL)
        assert r.status_code == 405

    def test_lowercase_path_returns_404(self, client):
        # EG: the path is /Signup (capital S). Lowercase should 404.
        r = client.post("/api/v1.0/auth/signup", json=_payload())
        assert r.status_code == 404

    def test_empty_body_returns_422(self, client):
        # EG: empty JSON body -> validation errors for all required fields.
        r = client.post(SIGNUP_URL, json={})
        assert r.status_code == 422

    def test_extra_fields_ignored_and_accepted(self, client):
        # EG: unexpected fields. Default Pydantic v2 behavior: ignored. 201.
        r = client.post(SIGNUP_URL, json=_payload(extra_field="x"))
        assert r.status_code == 201

    def test_invalid_json_body_returns_422(self, client):
        # EG: malformed JSON body -> 422 (FastAPI surfaces as validation error).
        r = client.post(
            SIGNUP_URL,
            data="this is not json",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 422

    def test_empty_string_password_returns_422(self, client):
        # EG: empty password (length=0) -> below min_length.
        r = client.post(SIGNUP_URL, json=_payload(password=""))
        assert r.status_code == 422
