"""LoftBox + CrewAI 최소 예제.

실행 전:
    pip install loftbox[crewai]
    export LOFTBOX_API_KEY=lb_live_xxx
    export OPENAI_API_KEY=sk-xxx   # CrewAI 기본 LLM
"""

from __future__ import annotations

import os

from loftbox import LoftBox
from loftbox.integrations.crewai import get_crewai_tools


def main() -> None:
    client = LoftBox(api_key=os.environ["LOFTBOX_API_KEY"])
    tools = get_crewai_tools(client)

    print(f"LoftBox 도구 {len(tools)}개: {[t.name for t in tools]}")

    # 실제 에이전트 연결 예 (선택 — crewai + LLM 필요):
    #
    #   from crewai import Agent, Task, Crew
    #
    #   support = Agent(
    #       role="이메일 지원 담당",
    #       goal="받은편지함을 확인하고 답장한다",
    #       backstory="LoftBox 메일박스를 운영하는 에이전트.",
    #       tools=tools,
    #   )
    #   task = Task(
    #       description="mb_123 받은편지함을 확인하고 요약하라",
    #       agent=support,
    #       expected_output="새 메일 요약",
    #   )
    #   Crew(agents=[support], tasks=[task]).kickoff()


if __name__ == "__main__":
    main()
