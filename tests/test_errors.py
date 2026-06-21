"""Tests for the deBridge error model and exception hierarchy."""

from debridge import DebridgeAPIError, DebridgeError


def test_api_error_is_a_debridge_error() -> None:
    err = DebridgeAPIError(
        error_id="UNKNOWN_ORDER",
        error_code=15,
        message="Order not found.",
        req_id="abc-123",
        status_code=400,
    )
    assert isinstance(err, DebridgeError)


def test_api_error_str_includes_id_and_message() -> None:
    err = DebridgeAPIError(
        error_id="COMPLIANCE_ADDRESS_BLOCKED",
        error_code=123,
        message="address is flagged",
        req_id="r-1",
        status_code=200,
    )
    text = str(err)
    assert "COMPLIANCE_ADDRESS_BLOCKED" in text
    assert "address is flagged" in text


def test_api_error_exposes_fields() -> None:
    err = DebridgeAPIError(
        error_id="INVALID_QUERY_PARAMETERS",
        error_code=2,
        message="bad id",
        req_id="r-2",
        status_code=400,
    )
    assert err.error_id == "INVALID_QUERY_PARAMETERS"
    assert err.error_code == 2
    assert err.req_id == "r-2"
    assert err.status_code == 400


def test_api_error_allows_missing_optional_fields() -> None:
    # Some error-like bodies (or non-JSON 5xx) may not carry every field.
    err = DebridgeAPIError(
        error_id=None,
        error_code=None,
        message="Internal Server Error",
        req_id=None,
        status_code=500,
    )
    assert err.status_code == 500
    assert "Internal Server Error" in str(err)
