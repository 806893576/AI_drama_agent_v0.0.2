"""版权与 IP 风险检查。"""

from __future__ import annotations

from safety.policies import COPYRIGHT_KEYWORDS, find_keywords


def detect_copyright_risks(text: str) -> list[str]:
    return find_keywords(text, COPYRIGHT_KEYWORDS)
