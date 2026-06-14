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

## 예제

`examples/quickstart.py` 참고.

## 라이선스

MIT
