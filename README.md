# LoftBox Python SDK

AI 에이전트를 위한 이메일 인프라 SDK.

## 설치

```bash
pip install loftbox
```

요구사항: Python 3.9+.

## 자가 가입 — 인증 없이 즉시 키 받기

콘솔 가입 없이 **인증 없는 한 번의 호출**로 바로 쓸 수 있는 API 키를 받습니다(제한 모드).
미검증 동안은 가입 시 선언한 owner 이메일하고만 발신·수신할 수 있고(닫힌 루프 PoC), owner 가
이메일로 클레임(검증)하면 제한이 풀립니다. 미검증 계정은 30일 후 자동 폐기됩니다.

```bash
curl -X POST https://api.loftbox.net/v1/auth/agent-signup \
  -H 'content-type: application/json' \
  -d '{"owner_email":"you@example.com","referrer":"my-app"}'
# → { "org_id": "...", "mailbox_address": "bot-...@mail.loftbox.net",
#     "api_key": "lb_live_...", "signup_status": "unverified", "claim": "..." }
```

받은 `api_key` 로 바로 SDK 를 초기화합니다. 제한 모드에선 `to` 가 owner 이메일이어야 합니다:

```python
from loftbox import LoftBox

with LoftBox(api_key="lb_live_...") as client:  # 자가 가입으로 받은 키
    # 제한 모드: 수신자는 owner 이메일만 허용(클레임 전)
    client.messages.send(mailbox_id=..., to=["you@example.com"],
                         subject="hello", body_text="from my agent")
```

클레임(owner 검증)은 `https://loftbox.net/claim?org=<org_id>` 또는 API
(`POST /v1/auth/claim/start` → `/v1/auth/claim/verify`)로 합니다. owner 에게는 가입 시
클레임 안내 메일이 자동 발송됩니다.

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
- **인바운드 안전 (#369/#370)**: `message.injection_score`/`injection_categories` (프롬프트-인젝션 휴리스틱 신호, 차단 아님) + `inbound_rules.*` (발신자 allow/block)

## 인바운드 안전 (프롬프트-인젝션 신호 + 발신자 통제)

수신 메일은 임의 외부 발신자가 보낸 untrusted 입력입니다. LoftBox 는 두 가지 통제를 제공합니다.

```python
# #369: 수신 메시지마다 프롬프트-인젝션 휴리스틱 점수(0~1) + 발화 카테고리.
#       신호 전용 — LoftBox 는 차단하지 않으며, 에이전트가 판단합니다.
for msg in client.mailboxes.list_inbox(mailbox_id).data:
    if (msg.injection_score or 0) >= 0.7:
        # 예: 사람 승인 후에만 메일 내 지시를 따른다.
        require_human_review(msg)

# #370: 발신자 allow/block 리스트로 *수신 자체*를 통제(SMTP 550 거부).
client.inbound_rules.create(rule_type="block", pattern_type="domain", pattern="evil.com")
client.inbound_rules.create(
    rule_type="allow", pattern_type="address",
    pattern="partner@trusted.com", mailbox_id="mb_xxx",  # 미지정 시 org 전체
)
rules = client.inbound_rules.list(mailbox_id="mb_xxx")
client.inbound_rules.remove("rule_id")
```

allow 리스트가 하나라도 있으면 미매치 발신자는 거부됩니다(화이트리스트). 평가는 위조 가능한
`From` 헤더가 아니라 SMTP envelope sender 로 합니다.

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
