"""LoftBox API 클라이언트 (동기, httpx 기반).

AI 에이전트를 위한 이메일 인프라. 핵심 플로우: 회원가입 → 에이전트/메일박스
생성 → 발송 → 수신 폴링/ack → 스레드 → 웹훅 → 승인.

사용 예:
    from loftbox import LoftBox

    client = LoftBox(api_key="lb_live_xxx")
    msg = client.messages.send(
        mailbox_id="mb_xxx",
        to=["recipient@example.com"],
        subject="Hello",
        body_text="World",
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from .errors import LoftBoxError, error_for_status
from .models import (
    Agent,
    Attachment,
    Domain,
    DomainStatus,
    InboundSenderRule,
    Mailbox,
    Message,
    Page,
    Suppression,
    Thread,
    Webhook,
)

DEFAULT_BASE_URL = "https://api.loftbox.net"
DEFAULT_TIMEOUT = 30.0
USER_AGENT = "loftbox-python/0.3.0"


class LoftBox:
    """LoftBox API 클라이언트.

    Args:
        api_key: API 키 (`Authorization: Bearer` 로 전송).
        base_url: API 베이스 URL (기본 https://api.loftbox.net).
        timeout: 요청 타임아웃(초).
        http_client: 직접 구성한 httpx.Client (테스트/프록시용). 주면 timeout 은
            그 클라이언트 설정을 따른다.
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key 는 필수입니다")
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout)

        # 리소스 네임스페이스
        self.auth = _Auth(self)
        self.agents = _Agents(self)
        self.mailboxes = _Mailboxes(self)
        self.messages = _Messages(self)
        self.threads = _Threads(self)
        self.webhooks = _Webhooks(self)
        self.domains = _Domains(self)
        self.suppressions = _Suppressions(self)
        self.inbound_rules = _InboundRules(self)
        self.attachments = _Attachments(self)

    # -- transport ----------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        hdrs = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if headers:
            hdrs.update(headers)
        # None 값 query param 제거.
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            resp = self._http.request(
                method, url, json=json, params=clean_params or None, headers=hdrs
            )
        except httpx.HTTPError as e:  # 네트워크/타임아웃 등
            raise LoftBoxError(f"요청 실패: {e}") from e

        request_id = resp.headers.get("x-request-id")
        if resp.status_code >= 400:
            body: Any = None
            message = f"HTTP {resp.status_code}"
            retry_after_secs: Optional[int] = None
            try:
                body = resp.json()
            except Exception:
                body = resp.text or None
                if body:
                    message = str(body)
            if isinstance(body, dict):
                # LoftBox 오류 wire shape: {"error": {message, code, retry_after, ...}}.
                # top-level message/detail 도 방어적으로 허용.
                err = body.get("error")
                if isinstance(err, dict):
                    message = err.get("message") or message
                    ra = err.get("retry_after")
                    if isinstance(ra, int):
                        retry_after_secs = ra
                else:
                    message = (
                        body.get("message")
                        or (err if isinstance(err, str) else None)
                        or body.get("detail")
                        or message
                    )
            # Retry-After 헤더가 있으면 우선(표준).
            header_ra = resp.headers.get("retry-after")
            if header_ra and header_ra.isdigit():
                retry_after_secs = int(header_ra)
            raise error_for_status(
                resp.status_code,
                message,
                body=body,
                request_id=request_id,
                retry_after_secs=retry_after_secs,
            )

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # -- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """소유한 httpx 클라이언트를 닫는다(외부 주입 클라이언트는 닫지 않음)."""
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> "LoftBox":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class _Resource:
    def __init__(self, client: LoftBox) -> None:
        self._c = client


class _Auth(_Resource):
    def signup(
        self,
        email: str,
        organization_name: str,
        slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """조직 가입 요청 — 이메일 검증 링크 발송. 반환은 서버 안내 페이로드."""
        return self._c._request(
            "POST",
            "/v1/auth/signup",
            json={"email": email, "organization_name": organization_name, "slug": slug},
        )

    def verify_signup(self, email: str, verification_token: str) -> Dict[str, Any]:
        """이메일 + 검증 토큰으로 가입 확정."""
        return self._c._request(
            "POST",
            "/v1/auth/signup/verify",
            json={"email": email, "verification_token": verification_token},
        )


class _Agents(_Resource):
    def create(
        self,
        name: str,
        slug: str,
        *,
        description: Optional[str] = None,
        purpose: Optional[str] = None,
        external_id: Optional[str] = None,
        owner_label: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Agent:
        body = {
            "name": name,
            "slug": slug,
            "description": description,
            "purpose": purpose,
            "external_id": external_id,
            "owner_label": owner_label,
            "metadata": metadata,
        }
        return Agent.model_validate(self._c._request("POST", "/v1/agents", json=body))

    def get(self, agent_id: str) -> Agent:
        return Agent.model_validate(self._c._request("GET", f"/v1/agents/{agent_id}"))

    def list(self, *, limit: Optional[int] = None, cursor: Optional[str] = None) -> Page[Agent]:
        raw = self._c._request("GET", "/v1/agents", params={"limit": limit, "cursor": cursor})
        return _page(raw, Agent)


class _Mailboxes(_Resource):
    def create(
        self,
        agent_id: str,
        local_part: str,
        *,
        domain_id: Optional[str] = None,
        display_name: Optional[str] = None,
        webhook_url: Optional[str] = None,
        retention_days: Optional[int] = None,
    ) -> Mailbox:
        body = {
            "local_part": local_part,
            "domain_id": domain_id,
            "display_name": display_name,
            "webhook_url": webhook_url,
            "retention_days": retention_days,
        }
        return Mailbox.model_validate(
            self._c._request("POST", f"/v1/agents/{agent_id}/mailboxes", json=body)
        )

    def list_by_agent(self, agent_id: str) -> Page[Mailbox]:
        raw = self._c._request("GET", f"/v1/agents/{agent_id}/mailboxes")
        return _page(raw, Mailbox)

    def list_inbox(
        self,
        mailbox_id: str,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Page[Message]:
        """미확인(unacked) 수신 메시지 폴링."""
        raw = self._c._request(
            "GET",
            f"/v1/mailboxes/{mailbox_id}/inbox",
            params={"limit": limit, "cursor": cursor},
        )
        return _page(raw, Message)

    def ack_inbox(self, mailbox_id: str, message_ids: List[str]) -> Any:
        """수신 메시지 확인 처리 — 다음 폴링에서 제외."""
        return self._c._request(
            "POST",
            f"/v1/mailboxes/{mailbox_id}/inbox/ack",
            json={"message_ids": message_ids},
        )


class _Messages(_Resource):
    def send(
        self,
        mailbox_id: str,
        to: List[str],
        subject: str,
        *,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        body_markdown: Optional[str] = None,
        cc: Optional[List[str]] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        send_at: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Message:
        """발송 큐에 메시지 진입.

        send_at(RFC3339 미래 시각)을 주면 예약발송. idempotency_key 를 주면
        같은 키+같은 내용 재요청은 원본 메시지를 그대로 반환(중복 발송 방지).
        """
        body: Dict[str, Any] = {
            "mailbox_id": mailbox_id,
            "to": to,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "body_markdown": body_markdown,
            "cc": cc or [],
            "in_reply_to": in_reply_to,
            "references": references or [],
            "metadata": metadata,
            "attachments": attachments or [],
            "send_at": send_at,
        }
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return Message.model_validate(
            self._c._request("POST", "/v1/messages", json=body, headers=headers)
        )

    def get(self, message_id: str) -> Message:
        return Message.model_validate(self._c._request("GET", f"/v1/messages/{message_id}"))

    def list(
        self,
        *,
        mailbox_id: Optional[str] = None,
        direction: Optional[str] = None,
        status: Optional[str] = None,
        label: Optional[str] = None,
        q: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Page[Message]:
        """메시지 목록 — mailbox/direction/status/label 필터, q 전문검색."""
        raw = self._c._request(
            "GET",
            "/v1/messages",
            params={
                "mailbox_id": mailbox_id,
                "direction": direction,
                "status": status,
                "label": label,
                "q": q,
                "limit": limit,
                "cursor": cursor,
            },
        )
        return _page(raw, Message)

    def add_labels(self, message_id: str, labels: List[str]) -> Message:
        return Message.model_validate(
            self._c._request("POST", f"/v1/messages/{message_id}/labels", json={"labels": labels})
        )

    def remove_label(self, message_id: str, label: str) -> Message:
        # 라벨을 경로 세그먼트로 안전 인코딩(공백/슬래시 등). safe="" 로 '/' 도 인코딩.
        seg = quote(label, safe="")
        return Message.model_validate(
            self._c._request("DELETE", f"/v1/messages/{message_id}/labels/{seg}")
        )

    def approve(self, message_id: str, reason: str) -> Message:
        return Message.model_validate(
            self._c._request("POST", f"/v1/messages/{message_id}/approve", json={"reason": reason})
        )

    def reject(self, message_id: str, reason: str) -> Message:
        return Message.model_validate(
            self._c._request("POST", f"/v1/messages/{message_id}/reject", json={"reason": reason})
        )


class _Threads(_Resource):
    def list(
        self,
        *,
        mailbox_id: Optional[str] = None,
        q: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Page[Thread]:
        raw = self._c._request(
            "GET",
            "/v1/threads",
            params={"mailbox_id": mailbox_id, "q": q, "limit": limit, "cursor": cursor},
        )
        return _page(raw, Thread)

    def list_messages(self, thread_id: str) -> Page[Message]:
        raw = self._c._request("GET", f"/v1/threads/{thread_id}/messages")
        return _page(raw, Message)


class _Webhooks(_Resource):
    def create(self, agent_id: str, url: str, event_types: List[str]) -> Webhook:
        return Webhook.model_validate(
            self._c._request(
                "POST",
                f"/v1/agents/{agent_id}/webhooks",
                json={"url": url, "event_types": event_types},
            )
        )


class _Domains(_Resource):
    def create(self, domain: str) -> Domain:
        return Domain.model_validate(
            self._c._request("POST", "/v1/domains", json={"domain": domain})
        )

    def list(self) -> Page[Domain]:
        return _page(self._c._request("GET", "/v1/domains"), Domain)

    def status(self, domain_id: str) -> DomainStatus:
        return DomainStatus.model_validate(
            self._c._request("GET", f"/v1/domains/{domain_id}/status")
        )


class _Suppressions(_Resource):
    def list(
        self, *, limit: Optional[int] = None, before: Optional[str] = None
    ) -> Page[Suppression]:
        raw = self._c._request("GET", "/v1/suppressions", params={"limit": limit, "before": before})
        return _page(raw, Suppression)

    def create(self, address: str) -> Suppression:
        return Suppression.model_validate(
            self._c._request("POST", "/v1/suppressions", json={"address": address})
        )

    def remove(self, suppression_id: str) -> None:
        self._c._request("DELETE", f"/v1/suppressions/{suppression_id}")


class _InboundRules(_Resource):
    """#370 인바운드 발신자 allow/block 리스트 — 수신 통제."""

    def list(
        self,
        *,
        mailbox_id: Optional[str] = None,
        limit: Optional[int] = None,
        before: Optional[str] = None,
    ) -> Page[InboundSenderRule]:
        raw = self._c._request(
            "GET",
            "/v1/inbound-rules",
            params={"mailbox_id": mailbox_id, "limit": limit, "before": before},
        )
        return _page(raw, InboundSenderRule)

    def create(
        self,
        *,
        rule_type: str,
        pattern_type: str,
        pattern: str,
        mailbox_id: Optional[str] = None,
    ) -> InboundSenderRule:
        """규칙 생성. rule_type=allow|block, pattern_type=address|domain.

        mailbox_id 미지정 = org 전체. block 매치 또는 allow 리스트 미매치 발신자는 수신 거부.
        """
        return InboundSenderRule.model_validate(
            self._c._request(
                "POST",
                "/v1/inbound-rules",
                json={
                    "rule_type": rule_type,
                    "pattern_type": pattern_type,
                    "pattern": pattern,
                    "mailbox_id": mailbox_id,
                },
            )
        )

    def remove(self, rule_id: str) -> None:
        self._c._request("DELETE", f"/v1/inbound-rules/{rule_id}")


class _Attachments(_Resource):
    def list_for_message(self, message_id: str) -> Page[Attachment]:
        raw = self._c._request("GET", f"/v1/messages/{message_id}/attachments")
        return _page(raw, Attachment)

    def presigned_url(self, attachment_id: str) -> Dict[str, Any]:
        return self._c._request("GET", f"/v1/attachments/{attachment_id}/url")


def _page(raw: Any, model: Type[BaseModel]) -> Page:
    """{data:[...], next_cursor} 또는 단순 배열 응답을 Page 로 정규화."""
    if isinstance(raw, list):
        return Page(data=[model.model_validate(x) for x in raw], next_cursor=None)
    src = raw or {}
    data = [model.model_validate(x) for x in src.get("data", [])]
    return Page(data=data, next_cursor=src.get("next_cursor"))
