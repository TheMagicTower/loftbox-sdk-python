"""LoftBox Python SDK — AI 에이전트를 위한 이메일 인프라."""

from .client import LoftBox
from .errors import (
    AuthenticationError,
    ConflictError,
    LoftBoxError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ValidationError,
)
from .models import (
    Agent,
    Attachment,
    Domain,
    DomainStatus,
    Mailbox,
    Message,
    Page,
    Suppression,
    Thread,
    Webhook,
)

__version__ = "0.2.0"
__all__ = [
    "LoftBox",
    # models
    "Agent",
    "Attachment",
    "Domain",
    "DomainStatus",
    "Mailbox",
    "Message",
    "Page",
    "Suppression",
    "Thread",
    "Webhook",
    # errors
    "LoftBoxError",
    "AuthenticationError",
    "PermissionError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ValidationError",
]
