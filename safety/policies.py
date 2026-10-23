"""安全策略定义。"""

from __future__ import annotations

BLOCK_KEYWORDS = ["真实身份证", "银行卡密码", "绕过审核", "规避平台审核", "冒充真人"]
REWRITE_KEYWORDS = ["一比一复刻", "完全复刻", "照搬", "模仿某部电影", "未成年人暧昧", "血腥细节"]
COPYRIGHT_KEYWORDS = ["迪士尼", "漫威", "哈利波特", "知名明星", "某部电影"]


def find_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]
