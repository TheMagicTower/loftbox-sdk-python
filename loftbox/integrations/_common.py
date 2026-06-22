"""LangChain / CrewAI 도구가 공유하는 인자 스키마 + 실행 로직.

도구별로 pydantic args_schema 와 실제 SDK 호출을 한곳에 정의해, 두 프레임워크
어댑터가 같은 동작을 갖도록 한다. SDK 가 반환하는 모델은 사람이 읽을 수 있는
문자열로 요약해서 LLM 컨텍스트에 넣는다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ..client import LoftBox
    from ..models import Message, Page


# -- 인자 스키마 ------------------------------------------------------------


class SendEmailArgs(BaseModel):
    """이메일 발송 인자."""

    mailbox_id: str = Field(description="발송에 사용할 메일박스 ID (mb_...)")
    to: List[str] = Field(description="수신자 이메일 주소 목록")
    subject: str = Field(description="이메일 제목")
    body_text: Optional[str] = Field(
        default=None, description="평문 본문. body_html 과 최소 하나는 필요."
    )
    body_html: Optional[str] = Field(default=None, description="HTML 본문(선택)")
    cc: Optional[List[str]] = Field(default=None, description="참조(cc) 주소 목록(선택)")
    in_reply_to: Optional[str] = Field(
        default=None, description="답장 시 원본 메시지의 Message-ID(선택)"
    )


class CheckInboxArgs(BaseModel):
    """미확인 수신 메시지 폴링 인자."""

    mailbox_id: str = Field(description="조회할 메일박스 ID (mb_...)")
    limit: Optional[int] = Field(default=None, description="가져올 최대 개수(선택)")
    cursor: Optional[str] = Field(default=None, description="다음 페이지 커서(선택)")


class ListMessagesArgs(BaseModel):
    """메시지 목록 조회 인자."""

    mailbox_id: Optional[str] = Field(default=None, description="메일박스 ID 필터(선택)")
    direction: Optional[str] = Field(
        default=None, description="방향 필터: 'inbound' 또는 'outbound'(선택)"
    )
    status: Optional[str] = Field(default=None, description="상태 필터(선택)")
    q: Optional[str] = Field(default=None, description="전문 검색어(선택)")
    limit: Optional[int] = Field(default=None, description="최대 개수(선택)")
    cursor: Optional[str] = Field(default=None, description="다음 페이지 커서(선택)")


class ApproveMessageArgs(BaseModel):
    """발송 승인 인자."""

    message_id: str = Field(description="승인할 메시지 ID (msg_...)")
    reason: str = Field(description="승인 사유 (감사 로그에 기록됨)")


class RejectMessageArgs(BaseModel):
    """발송 거부 인자."""

    message_id: str = Field(description="거부할 메시지 ID (msg_...)")
    reason: str = Field(description="거부 사유 (감사 로그에 기록됨)")


# -- 도구 메타 + 실행 -------------------------------------------------------

SEND_EMAIL_DESCRIPTION = (
    "LoftBox 메일박스에서 이메일을 발송한다. mailbox_id, 수신자(to), 제목(subject)이 "
    "필요하며 body_text 또는 body_html 중 하나 이상을 줘야 한다. 답장이면 in_reply_to 에 "
    "원본 Message-ID 를 넣는다."
)
CHECK_INBOX_DESCRIPTION = (
    "메일박스의 미확인(unacked) 수신 메시지를 폴링한다. 새로 도착한 이메일을 확인할 때 쓴다."
)
LIST_MESSAGES_DESCRIPTION = (
    "메시지 목록을 조회한다. mailbox_id/direction/status 로 필터하거나 q 로 전문 검색한다."
)
APPROVE_MESSAGE_DESCRIPTION = "승인 대기 중인 발송 메시지를 승인한다. 사유(reason)가 필요하다."
REJECT_MESSAGE_DESCRIPTION = "승인 대기 중인 발송 메시지를 거부한다. 사유(reason)가 필요하다."


def _summarize_message(msg: "Message") -> str:
    parts = [f"id={msg.id}"]
    if msg.status:
        parts.append(f"status={msg.status}")
    if msg.subject:
        parts.append(f"subject={msg.subject!r}")
    return "Message(" + ", ".join(parts) + ")"


def _summarize_page(page: "Page") -> str:
    if not page.data:
        return "메시지 없음."
    lines = [_summarize_message(m) for m in page.data]
    out = f"{len(page.data)}건:\n" + "\n".join(lines)
    if page.next_cursor:
        out += f"\nnext_cursor={page.next_cursor}"
    return out


def run_send_email(
    client: "LoftBox",
    mailbox_id: str,
    to: List[str],
    subject: str,
    body_text: Optional[str] = None,
    body_html: Optional[str] = None,
    cc: Optional[List[str]] = None,
    in_reply_to: Optional[str] = None,
) -> str:
    msg = client.messages.send(
        mailbox_id=mailbox_id,
        to=to,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        cc=cc,
        in_reply_to=in_reply_to,
    )
    return "발송됨: " + _summarize_message(msg)


def run_check_inbox(
    client: "LoftBox",
    mailbox_id: str,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> str:
    page = client.mailboxes.list_inbox(mailbox_id, limit=limit, cursor=cursor)
    return _summarize_page(page)


def run_list_messages(
    client: "LoftBox",
    mailbox_id: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> str:
    page = client.messages.list(
        mailbox_id=mailbox_id,
        direction=direction,
        status=status,
        q=q,
        limit=limit,
        cursor=cursor,
    )
    return _summarize_page(page)


def run_approve_message(client: "LoftBox", message_id: str, reason: str) -> str:
    msg = client.messages.approve(message_id, reason)
    return "승인됨: " + _summarize_message(msg)


def run_reject_message(client: "LoftBox", message_id: str, reason: str) -> str:
    msg = client.messages.reject(message_id, reason)
    return "거부됨: " + _summarize_message(msg)
