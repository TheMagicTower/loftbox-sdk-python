"""LoftBox 도구의 CrewAI 통합.

crewai 의 ``BaseTool`` 로 SDK 메서드를 노출한다. 사용:

    from loftbox import LoftBox
    from loftbox.integrations.crewai import get_crewai_tools

    client = LoftBox(api_key="lb_live_xxx")
    tools = get_crewai_tools(client)
    # tools 를 CrewAI Agent(tools=tools) 에 전달

crewai 가 설치돼 있지 않으면 import 시 친절한 ImportError 를 던진다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Type

from pydantic import BaseModel, PrivateAttr

try:
    from crewai.tools import BaseTool
except ImportError as exc:  # pragma: no cover - import-guard
    raise ImportError(
        "CrewAI 통합을 쓰려면 crewai 가 필요합니다. 설치: pip install loftbox[crewai]"
    ) from exc

from . import _common

if TYPE_CHECKING:
    from ..client import LoftBox


class _LoftBoxBaseTool(BaseTool):
    """LoftBox 클라이언트를 들고 있는 CrewAI 도구 베이스.

    crewai ``BaseTool`` 은 pydantic 모델이라, 클라이언트는 PrivateAttr 로 저장한다.
    인바운드 인젝션 가드 설정도 PrivateAttr 로 함께 보관한다.
    """

    _client: "LoftBox" = PrivateAttr()
    _injection_threshold: float = PrivateAttr(default=_common.DEFAULT_INJECTION_THRESHOLD)
    _block_high_injection: bool = PrivateAttr(default=False)

    def __init__(
        self,
        client: "LoftBox",
        *,
        injection_threshold: float = _common.DEFAULT_INJECTION_THRESHOLD,
        block_high_injection: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._client = client
        self._injection_threshold = injection_threshold
        self._block_high_injection = block_high_injection


class SendEmailTool(_LoftBoxBaseTool):
    name: str = "send_email"
    description: str = _common.SEND_EMAIL_DESCRIPTION
    args_schema: Type[BaseModel] = _common.SendEmailArgs

    def _run(
        self,
        mailbox_id: str,
        to: List[str],
        subject: str,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        in_reply_to: Optional[str] = None,
    ) -> str:
        return _common.run_send_email(
            self._client,
            mailbox_id=mailbox_id,
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            in_reply_to=in_reply_to,
        )


class CheckInboxTool(_LoftBoxBaseTool):
    name: str = "check_inbox"
    description: str = _common.CHECK_INBOX_DESCRIPTION
    args_schema: Type[BaseModel] = _common.CheckInboxArgs

    def _run(
        self, mailbox_id: str, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> str:
        return _common.run_check_inbox(
            self._client,
            mailbox_id=mailbox_id,
            limit=limit,
            cursor=cursor,
            injection_threshold=self._injection_threshold,
            block_high_injection=self._block_high_injection,
        )


class ListMessagesTool(_LoftBoxBaseTool):
    name: str = "list_messages"
    description: str = _common.LIST_MESSAGES_DESCRIPTION
    args_schema: Type[BaseModel] = _common.ListMessagesArgs

    def _run(
        self,
        mailbox_id: Optional[str] = None,
        direction: Optional[str] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> str:
        return _common.run_list_messages(
            self._client,
            mailbox_id=mailbox_id,
            direction=direction,
            status=status,
            q=q,
            limit=limit,
            cursor=cursor,
            injection_threshold=self._injection_threshold,
            block_high_injection=self._block_high_injection,
        )


class ApproveMessageTool(_LoftBoxBaseTool):
    name: str = "approve_message"
    description: str = _common.APPROVE_MESSAGE_DESCRIPTION
    args_schema: Type[BaseModel] = _common.ApproveMessageArgs

    def _run(self, message_id: str, reason: str) -> str:
        return _common.run_approve_message(self._client, message_id=message_id, reason=reason)


class RejectMessageTool(_LoftBoxBaseTool):
    name: str = "reject_message"
    description: str = _common.REJECT_MESSAGE_DESCRIPTION
    args_schema: Type[BaseModel] = _common.RejectMessageArgs

    def _run(self, message_id: str, reason: str) -> str:
        return _common.run_reject_message(self._client, message_id=message_id, reason=reason)


def get_crewai_tools(
    client: "LoftBox",
    *,
    injection_threshold: float = _common.DEFAULT_INJECTION_THRESHOLD,
    block_high_injection: bool = False,
) -> List[BaseTool]:
    """CrewAI Agent 에 넘길 LoftBox 도구 목록.

    injection_threshold/block_high_injection 으로 수신 메일 인젝션 가드를 조정한다
    (check_inbox/list_messages 에 적용).
    """
    return [
        SendEmailTool(client),
        CheckInboxTool(
            client,
            injection_threshold=injection_threshold,
            block_high_injection=block_high_injection,
        ),
        ListMessagesTool(
            client,
            injection_threshold=injection_threshold,
            block_high_injection=block_high_injection,
        ),
        ApproveMessageTool(client),
        RejectMessageTool(client),
    ]


__all__ = [
    "get_crewai_tools",
    "SendEmailTool",
    "CheckInboxTool",
    "ListMessagesTool",
    "ApproveMessageTool",
    "RejectMessageTool",
]
