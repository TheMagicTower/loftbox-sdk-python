"""LoftBox 데이터 모델 (pydantic v2).

API 응답을 그대로 받되, 서버가 필드를 추가해도 깨지지 않도록 `extra="allow"`.
알 수 없는 필드는 보존되어 `.model_extra` 로 접근 가능.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow")


class Agent(_Base):
    id: str
    slug: Optional[str] = None
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class Mailbox(_Base):
    id: str
    agent_id: Optional[str] = None
    address: str
    display_name: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = None


class Attachment(_Base):
    id: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None


class Message(_Base):
    id: str
    public_id: Optional[str] = None
    mailbox_id: Optional[str] = None
    thread_id: Optional[str] = None
    direction: Optional[str] = None
    status: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    body_markdown: Optional[str] = None
    # #229 수신 답장 본문(인용 제거)
    extracted_text: Optional[str] = None
    # #236 라벨
    labels: List[str] = Field(default_factory=list)
    # #241 예약발송 시각
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class Thread(_Base):
    id: str
    mailbox_id: Optional[str] = None
    subject: Optional[str] = None
    last_message_at: Optional[datetime] = None


class Webhook(_Base):
    id: str
    url: str
    event_types: List[str] = Field(default_factory=list)
    # 생성 응답에서 1회만 반환되는 서명 시크릿. 이후 조회에서는 None.
    # 받은 즉시 안전한 곳에 저장할 것 — 로그에 남기지 말 것.
    secret: Optional[str] = None


class Domain(_Base):
    id: str
    domain: Optional[str] = None
    status: Optional[str] = None


class DomainStatus(_Base):
    """`domains.status()` 응답 — id 없이 도메인 검증 상태."""

    domain: Optional[str] = None
    status: Optional[str] = None
    inbound: Optional[object] = None
    outbound: Optional[object] = None
    next_actions: Optional[object] = None


class Suppression(_Base):
    id: str
    address: str
    reason: Optional[str] = None
    created_at: Optional[datetime] = None


class Page(_Base, Generic[T]):
    """cursor 페이지네이션 응답 래퍼.

    `data` 는 항목 리스트, `next_cursor` 가 있으면 다음 페이지 요청에 전달.
    """

    data: List[T] = Field(default_factory=list)
    next_cursor: Optional[str] = None
