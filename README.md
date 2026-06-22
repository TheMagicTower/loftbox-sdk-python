# LoftBox Python SDK

AI 에이전트를 위한 이메일 인프라 SDK.

## 설치

```bash
pip install loftbox
```

요구사항: Python 3.9+.

## 빠른 시작

```python
from loftbox import LoftBox

with LoftBox(api_key="lb_live_xxx") as client:
    # 에이전트 + 메일박스
    agent = client.agents.create(name="Support Bot", slug="support-bot")
    mailbox = client.mailboxes.create(agent.id, local_part="support")

    # 발송 (멱등 키로 중복 방지)
    msg = client.messages.send(
        mailbox_id=mailbox.id,
        to=["recipient@example.com"],
        subject="Hello",
        body_text="World",
        idempotency_key="welcome-42",
    )

    # 수신 폴링 → ack
    inbox = client.mailboxes.list_inbox(mailbox.id)
    client.mailboxes.ack_inbox(mailbox.id, [m.id for m in inbox.data])
```

## 기능

- **발송**: `messages.send(...)` — 텍스트/HTML/Markdown 본문, 첨부, cc, 답장 헤더
- **예약 발송**: `send(..., send_at="2030-01-01T09:00:00Z")` (미래 RFC3339)
- **멱등 발송**: `send(..., idempotency_key="...")` — 중복 발송 방지
- **수신**: `mailboxes.list_inbox(...)` 폴링 + `ack_inbox(...)`. `message.extracted_text` 로 인용 제거된 답장 본문
- **라벨**: `messages.add_labels(...)`, `remove_label(...)`, `list(label=...)`
- **전문검색**: `messages.list(q="...")`, `threads.list(q="...")`
- **스레드**: `threads.list(...)`, `list_messages(...)`
- **승인 워크플로**: `messages.approve(id, reason=...)`, `reject(...)`
- **웹훅**: `webhooks.create(agent_id, url, event_types)`
- **도메인 / suppression**: `domains.*`, `suppressions.*`

## 오류 처리

모든 호출은 실패 시 `LoftBoxError` 하위 예외를 던집니다:

```python
from loftbox import RateLimitError, NotFoundError, ValidationError

try:
    client.messages.send(...)
except RateLimitError as e:
    print(f"{e.retry_after_secs}s 후 재시도")
except (NotFoundError, ValidationError) as e:
    print(e.status_code, e.message)
```

## 페이지네이션

목록 메서드는 `Page` 를 반환합니다 (`.data`, `.next_cursor`):

```python
page = client.messages.list(mailbox_id=mailbox.id, limit=50)
while True:
    for m in page.data:
        ...
    if not page.next_cursor:
        break
    page = client.messages.list(mailbox_id=mailbox.id, limit=50, cursor=page.next_cursor)
```

## 프레임워크 통합 (LangChain / CrewAI)

LoftBox 도구를 LLM 에이전트 프레임워크에 그대로 꽂을 수 있습니다. 노출 도구:
`send_email`, `check_inbox`, `list_messages`, `approve_message`, `reject_message`.

각 프레임워크는 선택 의존성으로 설치합니다(미설치 시에도 base SDK 는 정상 동작):

```bash
pip install loftbox[langchain]   # LangChain
pip install loftbox[crewai]      # CrewAI
```

### LangChain

```python
from loftbox import LoftBox
from loftbox.integrations.langchain import LoftBoxToolkit

client = LoftBox(api_key="lb_live_xxx")
tools = LoftBoxToolkit(client).get_tools()

# tools 를 LangChain 에이전트에 전달
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
prompt = ChatPromptTemplate.from_messages([
    ("system", "너는 이메일을 다루는 에이전트다."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])
agent = create_tool_calling_agent(llm, tools, prompt)
AgentExecutor(agent=agent, tools=tools).invoke(
    {"input": "mb_123 받은편지함에 새 메일 있는지 확인해줘"}
)
```

전체 예제: `examples/langchain_agent.py`.

### CrewAI

```python
from loftbox import LoftBox
from loftbox.integrations.crewai import get_crewai_tools
from crewai import Agent, Task, Crew

client = LoftBox(api_key="lb_live_xxx")
tools = get_crewai_tools(client)

support = Agent(
    role="이메일 지원 담당",
    goal="받은편지함을 확인하고 답장한다",
    backstory="LoftBox 메일박스를 운영하는 에이전트.",
    tools=tools,
)
task = Task(
    description="mb_123 받은편지함을 확인하고 요약하라",
    agent=support,
    expected_output="새 메일 요약",
)
Crew(agents=[support], tasks=[task]).kickoff()
```

전체 예제: `examples/crewai_agent.py`.

## 예제

`examples/quickstart.py` 참고.

## 라이선스

MIT
