"""LoftBox 도구의 LangChain 통합.

langchain_core 의 StructuredTool 로 SDK 메서드를 노출한다. 사용:

    from loftbox import LoftBox
    from loftbox.integrations.langchain import LoftBoxToolkit

    client = LoftBox(api_key="lb_live_xxx")
    tools = LoftBoxToolkit(client).get_tools()
    # tools 를 LangChain 에이전트에 그대로 전달

langchain_core 가 설치돼 있지 않으면 import 시 친절한 ImportError 를 던진다.
"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, List

try:
    from langchain_core.tools import StructuredTool
except ImportError as exc:  # pragma: no cover - import-guard
    raise ImportError(
        "LangChain 통합을 쓰려면 langchain-core 가 필요합니다. 설치: pip install loftbox[langchain]"
    ) from exc

from . import _common

if TYPE_CHECKING:
    from ..client import LoftBox


class LoftBoxToolkit:
    """LoftBox 클라이언트를 LangChain 도구 묶음으로 변환한다.

    Args:
        client: 인증된 ``LoftBox`` 클라이언트.
        injection_threshold: 이 점수 이상의 수신 메일을 고위험으로 보고 ⚠️ 경고를
            붙인다(0.0~1.0, 기본 0.7).
        block_high_injection: True 면 고위험 메일의 제목을 차단(strict 모드).
    """

    def __init__(
        self,
        client: "LoftBox",
        *,
        injection_threshold: float = _common.DEFAULT_INJECTION_THRESHOLD,
        block_high_injection: bool = False,
    ) -> None:
        self._client = client
        self._injection_threshold = injection_threshold
        self._block_high_injection = block_high_injection

    def get_tools(self) -> List["StructuredTool"]:
        """LangChain 에이전트에 넘길 ``StructuredTool`` 목록."""
        c = self._client
        threshold = self._injection_threshold
        block = self._block_high_injection
        return [
            StructuredTool.from_function(
                func=partial(_common.run_send_email, c),
                name="send_email",
                description=_common.SEND_EMAIL_DESCRIPTION,
                args_schema=_common.SendEmailArgs,
            ),
            StructuredTool.from_function(
                func=partial(
                    _common.run_check_inbox,
                    c,
                    injection_threshold=threshold,
                    block_high_injection=block,
                ),
                name="check_inbox",
                description=_common.CHECK_INBOX_DESCRIPTION,
                args_schema=_common.CheckInboxArgs,
            ),
            StructuredTool.from_function(
                func=partial(
                    _common.run_list_messages,
                    c,
                    injection_threshold=threshold,
                    block_high_injection=block,
                ),
                name="list_messages",
                description=_common.LIST_MESSAGES_DESCRIPTION,
                args_schema=_common.ListMessagesArgs,
            ),
            StructuredTool.from_function(
                func=partial(_common.run_approve_message, c),
                name="approve_message",
                description=_common.APPROVE_MESSAGE_DESCRIPTION,
                args_schema=_common.ApproveMessageArgs,
            ),
            StructuredTool.from_function(
                func=partial(_common.run_reject_message, c),
                name="reject_message",
                description=_common.REJECT_MESSAGE_DESCRIPTION,
                args_schema=_common.RejectMessageArgs,
            ),
        ]


__all__ = ["LoftBoxToolkit"]
