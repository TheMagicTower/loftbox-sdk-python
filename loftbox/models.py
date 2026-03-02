"""LoftBox 데이터 모델"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Agent:
    id: str
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Mailbox:
    id: str
    agent_id: str
    address: str
    display_name: Optional[str] = None
    active: bool = True


@dataclass
class Message:
    id: str
    mailbox_id: str
    direction: str
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    status: str = "queued"
