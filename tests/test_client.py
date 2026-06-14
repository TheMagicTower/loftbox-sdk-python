"""LoftBox SDK 단위 테스트 — httpx.MockTransport 로 네트워크 없이 검증."""

from __future__ import annotations

import json
from typing import Callable, List, Tuple

import httpx
import pytest

from loftbox import (
    ConflictError,
    LoftBox,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

Captured = List[httpx.Request]


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> Tuple[LoftBox, Captured]:
    captured: Captured = []

    def wrapper(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return handler(request)

    transport = httpx.MockTransport(wrapper)
    http = httpx.Client(transport=transport, base_url="https://api.test")
    client = LoftBox(api_key="lb_test_key", base_url="https://api.test", http_client=http)
    return client, captured


def test_requires_api_key() -> None:
    with pytest.raises(ValueError):
        LoftBox(api_key="")


def test_send_shapes_request_and_parses_message() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "POST"
        assert req.url.path == "/v1/messages"
        assert req.headers["authorization"] == "Bearer lb_test_key"
        assert req.headers["idempotency-key"] == "key-1"
        body = json.loads(req.content)
        assert body["mailbox_id"] == "mb_1"
        assert body["to"] == ["a@example.com"]
        assert body["send_at"] == "2030-01-01T00:00:00+00:00"
        return httpx.Response(201, json={"id": "msg_1", "status": "queued", "labels": []})

    client, _ = make_client(handler)
    msg = client.messages.send(
        mailbox_id="mb_1",
        to=["a@example.com"],
        subject="hi",
        body_text="b",
        send_at="2030-01-01T00:00:00+00:00",
        idempotency_key="key-1",
    )
    assert msg.id == "msg_1"
    assert msg.status == "queued"


def test_list_messages_filters_and_pagination() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/v1/messages"
        params = dict(req.url.params)
        assert params["label"] == "vip"
        assert params["q"] == "invoice"
        # None 값은 빠져야 함.
        assert "status" not in params
        return httpx.Response(
            200,
            json={"data": [{"id": "m1", "labels": ["vip"]}], "next_cursor": "c2"},
        )

    client, _ = make_client(handler)
    page = client.messages.list(label="vip", q="invoice", limit=10)
    assert len(page.data) == 1
    assert page.data[0].id == "m1"
    assert page.next_cursor == "c2"


def test_list_handles_bare_array_response() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": "d1", "domain": "x.com"}])

    client, _ = make_client(handler)
    page = client.domains.list()
    assert len(page.data) == 1
    assert page.data[0].id == "d1"
    assert page.next_cursor is None


def test_ack_inbox_posts_ids() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/v1/mailboxes/mb_1/inbox/ack"
        assert json.loads(req.content)["message_ids"] == ["m1", "m2"]
        return httpx.Response(200, json={"acked": 2})

    client, _ = make_client(handler)
    client.mailboxes.ack_inbox("mb_1", ["m1", "m2"])


def test_remove_label_uses_path_segment() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "DELETE"
        assert req.url.path == "/v1/messages/msg_1/labels/vip"
        return httpx.Response(200, json={"id": "msg_1", "labels": []})

    client, _ = make_client(handler)
    msg = client.messages.remove_label("msg_1", "vip")
    assert msg.labels == []


def test_error_mapping() -> None:
    cases = [
        (400, ValidationError),
        (404, NotFoundError),
        (409, ConflictError),
    ]
    for code, exc in cases:
        client, _ = make_client(lambda req, c=code: httpx.Response(c, json={"message": f"err {c}"}))
        with pytest.raises(exc) as ei:
            client.messages.get("msg_x")
        assert ei.value.status_code == code
        assert "err" in ei.value.message


def test_rate_limit_retry_after() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "12"}, json={"message": "slow down"})

    client, _ = make_client(handler)
    with pytest.raises(RateLimitError) as ei:
        client.messages.send(mailbox_id="mb_1", to=["a@b.com"], subject="s", body_text="b")
    assert ei.value.retry_after_secs == 12


def test_nested_error_shape_and_retry_after_body() -> None:
    # LoftBox 실제 오류 wire shape: {"error": {message, retry_after, ...}}.
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error": {"message": "rate limited", "code": 429, "retry_after": 7}},
        )

    client, _ = make_client(handler)
    with pytest.raises(RateLimitError) as ei:
        client.messages.send(mailbox_id="mb_1", to=["a@b.com"], subject="s", body_text="b")
    assert ei.value.message == "rate limited"
    assert ei.value.retry_after_secs == 7


def test_verify_signup_sends_email_and_token() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/v1/auth/signup/verify"
        body = json.loads(req.content)
        assert body == {"email": "a@b.com", "verification_token": "tok-1"}
        return httpx.Response(200, json={"ok": True})

    client, _ = make_client(handler)
    client.auth.verify_signup("a@b.com", "tok-1")


def test_remove_label_encodes_special_chars() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        # 'needs review/urgent' → 슬래시·공백 인코딩되어 단일 세그먼트로(raw_path).
        assert req.url.raw_path.decode() == "/v1/messages/msg_1/labels/needs%20review%2Furgent"
        return httpx.Response(200, json={"id": "msg_1", "labels": []})

    client, _ = make_client(handler)
    client.messages.remove_label("msg_1", "needs review/urgent")


def test_domain_status_parses_without_id() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"domain": "x.com", "status": "verified", "inbound": {"mx": True}},
        )

    client, _ = make_client(handler)
    st = client.domains.status("dom_1")
    assert st.domain == "x.com"
    assert st.status == "verified"


def test_context_manager_closes() -> None:
    client, _ = make_client(lambda req: httpx.Response(200, json={"data": []}))
    with client as c:
        c.agents.list()
