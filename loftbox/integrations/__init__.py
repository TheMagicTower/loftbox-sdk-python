"""프레임워크 통합 — LangChain / CrewAI 도구.

서브모듈은 lazy/guarded import 한다. 해당 프레임워크가 설치돼 있지 않아도
`import loftbox` 와 base SDK 는 깨지지 않는다. 통합을 쓰려면:

    pip install loftbox[langchain]   # LangChain
    pip install loftbox[crewai]      # CrewAI

서브모듈 import 시점에 프레임워크 미설치면 친절한 ImportError 를 던진다:

    from loftbox.integrations.langchain import LoftBoxToolkit
    from loftbox.integrations.crewai import get_crewai_tools
"""

from __future__ import annotations

__all__ = ["langchain", "crewai"]
