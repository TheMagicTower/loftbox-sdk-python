"""LoftBox SDK 예외."""

from __future__ import annotations

from typing import Optional


class LoftBoxError(Exception):
    """LoftBox API 호출 실패의 기본 예외.

    Attributes:
        status_code: HTTP 상태 코드 (네트워크 오류 시 None).
        message: 서버가 준 오류 메시지(가능하면) 또는 예외 메시지.
        body: 파싱된 응답 본문(dict) 또는 원문(str), 없으면 None.
        request_id: 서버 X-Request-Id 헤더(있으면) — 지원 문의용.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: object = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.body = body
        self.request_id = request_id


class AuthenticationError(LoftBoxError):
    """401 — API 키가 없거나 유효하지 않음."""


class PermissionError(LoftBoxError):
    """403 — API 키에 필요한 scope 가 없음."""


class NotFoundError(LoftBoxError):
    """404 — 리소스를 찾을 수 없음."""


class ConflictError(LoftBoxError):
    """409 — 멱등 키 충돌 / 상태 충돌(예: suppression 차단)."""


class RateLimitError(LoftBoxError):
    """429 — 발송 rate limit 초과.

    `retry_after_secs` 가 있으면 그만큼 기다린 뒤 재시도.
    """

    def __init__(
        self, *args: object, retry_after_secs: Optional[int] = None, **kwargs: object
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.retry_after_secs = retry_after_secs


class ValidationError(LoftBoxError):
    """400 — 요청 검증 실패."""


def error_for_status(
    status_code: int,
    message: str,
    *,
    body: object = None,
    request_id: Optional[str] = None,
    retry_after_secs: Optional[int] = None,
) -> LoftBoxError:
    """HTTP 상태 코드를 구체 예외 타입으로 매핑."""
    common = {"status_code": status_code, "body": body, "request_id": request_id}
    if status_code in (400, 422):
        return ValidationError(message, **common)  # type: ignore[arg-type]
    if status_code == 401:
        return AuthenticationError(message, **common)  # type: ignore[arg-type]
    if status_code == 403:
        return PermissionError(message, **common)  # type: ignore[arg-type]
    if status_code == 404:
        return NotFoundError(message, **common)  # type: ignore[arg-type]
    if status_code == 409:
        return ConflictError(message, **common)  # type: ignore[arg-type]
    if status_code == 429:
        return RateLimitError(message, retry_after_secs=retry_after_secs, **common)  # type: ignore[arg-type]
    return LoftBoxError(message, **common)  # type: ignore[arg-type]
