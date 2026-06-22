"""LoftBox + LangChain 최소 예제.

실행 전:
    pip install loftbox[langchain] langchain-openai
    export LOFTBOX_API_KEY=lb_live_xxx
    export OPENAI_API_KEY=sk-xxx
"""

from __future__ import annotations

import os

from loftbox import LoftBox
from loftbox.integrations.langchain import LoftBoxToolkit


def main() -> None:
    client = LoftBox(api_key=os.environ["LOFTBOX_API_KEY"])
    tools = LoftBoxToolkit(client).get_tools()

    print(f"LoftBox 도구 {len(tools)}개: {[t.name for t in tools]}")

    # 실제 에이전트 연결 예 (선택 — langchain + LLM 필요):
    #
    #   from langchain.agents import create_tool_calling_agent, AgentExecutor
    #   from langchain_core.prompts import ChatPromptTemplate
    #   from langchain_openai import ChatOpenAI
    #
    #   llm = ChatOpenAI(model="gpt-4o-mini")
    #   prompt = ChatPromptTemplate.from_messages([
    #       ("system", "너는 이메일을 다루는 에이전트다."),
    #       ("human", "{input}"),
    #       ("placeholder", "{agent_scratchpad}"),
    #   ])
    #   agent = create_tool_calling_agent(llm, tools, prompt)
    #   executor = AgentExecutor(agent=agent, tools=tools)
    #   executor.invoke({"input": "mb_123 받은편지함에 새 메일 있는지 확인해줘"})


if __name__ == "__main__":
    main()
