"""LoftBox Python SDK 퀵스타트.

실행:
    export LOFTBOX_API_KEY=lb_live_xxx
    python examples/quickstart.py
"""

import os

from loftbox import LoftBox, RateLimitError


def main() -> None:
    api_key = os.environ["LOFTBOX_API_KEY"]

    with LoftBox(api_key=api_key) as client:
        # 1. 에이전트 + 메일박스 준비 (최초 1회).
        agent = client.agents.create(name="Support Bot", slug="support-bot")
        mailbox = client.mailboxes.create(agent.id, local_part="support")
        print(f"mailbox: {mailbox.address}")

        # 2. 발송 (멱등 키로 중복 방지).
        try:
            msg = client.messages.send(
                mailbox_id=mailbox.id,
                to=["customer@example.com"],
                subject="안녕하세요",
                body_text="LoftBox 에서 보냅니다.",
                idempotency_key="welcome-customer-42",
            )
            print(f"sent: {msg.id} status={msg.status}")
        except RateLimitError as e:
            print(f"rate limited, retry after {e.retry_after_secs}s")

        # 3. 예약 발송 (1시간 뒤).
        from datetime import datetime, timedelta, timezone

        client.messages.send(
            mailbox_id=mailbox.id,
            to=["customer@example.com"],
            subject="리마인더",
            body_text="예약 발송 메시지",
            send_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        )

        # 4. 수신 폴링 → 처리 → ack.
        inbox = client.mailboxes.list_inbox(mailbox.id, limit=20)
        for incoming in inbox.data:
            print(f"received: {incoming.subject} (extracted: {incoming.extracted_text!r})")
        if inbox.data:
            client.mailboxes.ack_inbox(mailbox.id, [m.id for m in inbox.data])

        # 5. 라벨링 + 전문검색.
        if inbox.data:
            client.messages.add_labels(inbox.data[0].id, ["needs-reply", "vip"])
        results = client.messages.list(q="invoice", label="vip", limit=10)
        print(f"search hits: {len(results.data)}")


if __name__ == "__main__":
    main()
