# LoftBox Python SDK

AI 에이전트를 위한 이메일 인프라 SDK

## 설치

```bash
pip install loftbox
```

## 사용법

```python
from loftbox import LoftBox

client = LoftBox(api_key="lb_live_xxx")
client.messages.send(
    mailbox_id="mb_xxx",
    to="recipient@example.com",
    subject="Hello",
    body_text="World"
)
```

## 프레임워크 통합

### LangChain

```bash
pip install loftbox[langchain]
```

### CrewAI

```bash
pip install loftbox[crewai]
```
