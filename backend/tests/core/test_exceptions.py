import pytest

from app.core.exceptions import (
    AppException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    QuotaExceededException,
    UnauthorizedException,
    ValidationException,
)


class TestAppException:
    def test_defaults_are_applied(self) -> None:
        exc = AppException("Something went wrong")

        assert isinstance(exc, Exception)
        assert exc.detail == "Something went wrong"
        assert exc.code == "UNKNOWN"
        assert exc.status_code == 400

    def test_custom_values_override_defaults(self) -> None:
        exc = AppException(
            detail="Custom detail",
            code="CUSTOM_CODE",
            status_code=499,
        )

        assert exc.detail == "Custom detail"
        assert exc.code == "CUSTOM_CODE"
        assert exc.status_code == 499


@pytest.mark.parametrize(
    ("exception_cls", "default_detail", "default_code", "default_status_code"),
    [
        (NotFoundException, "Resource not found", "NOT_FOUND", 404),
        (UnauthorizedException, "Unauthorized", "UNAUTHORIZED", 401),
        (ForbiddenException, "Forbidden", "FORBIDDEN", 403),
        (ConflictException, "Conflict", "CONFLICT", 409),
        (QuotaExceededException, "Quota exceeded", "QUOTA_EXCEEDED", 429),
        (ValidationException, "Validation error", "VALIDATION_ERROR", 422),
    ],
)
def test_exception_subclasses_defaults_and_custom_detail(
    exception_cls,
    default_detail: str,
    default_code: str,
    default_status_code: int,
) -> None:
    default_exc = exception_cls()
    custom_exc = exception_cls("Custom detail")

    assert issubclass(exception_cls, AppException)
    assert issubclass(exception_cls, Exception)

    assert default_exc.detail == default_detail
    assert default_exc.code == default_code
    assert default_exc.status_code == default_status_code

    assert custom_exc.detail == "Custom detail"
    assert custom_exc.code == default_code
    assert custom_exc.status_code == default_status_code
