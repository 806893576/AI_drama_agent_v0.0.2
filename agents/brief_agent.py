"""需求分析 Agent。

职责：把用户自然语言需求解析为 CreativeBrief。
运行策略：配置真实 LLM 时优先调用模型；未配置或模型输出异常时，使用规则解析兜底。
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from domain.brief.schemas import BriefValidation, CreativeBrief
from domain.brief.validators import validate_brief
from services.llm import LLMStructuredOutputError, StructuredLLMRunner, llm_enabled


class BriefAnalysisResult(BaseModel):
    creative_brief: CreativeBrief
    validation: BriefValidation
    used_llm: bool = False
    llm_error: str | None = None


class BriefAgent:
    def __init__(self, llm_runner: StructuredLLMRunner | None = None) -> None:
        self.llm_runner = llm_runner

    def analyze(self, user_request: str) -> BriefAnalysisResult:
        if _llm_enabled():
            try:
                brief, _response = (self.llm_runner or StructuredLLMRunner()).generate_model(
                    "brief_agent",
                    {"user_request": user_request},
                    CreativeBrief,
                    temperature=0.1,
                )
                return BriefAnalysisResult(
                    creative_brief=brief,
                    validation=validate_brief(brief),
                    used_llm=True,
                )
            except LLMStructuredOutputError:
                raise
            except Exception as exc:
                fallback = self._analyze_by_rules(user_request)
                return BriefAnalysisResult(
                    creative_brief=fallback,
                    validation=validate_brief(fallback),
                    used_llm=False,
                    llm_error=str(exc),
                )

        brief = self._analyze_by_rules(user_request)
        return BriefAnalysisResult(creative_brief=brief, validation=validate_brief(brief))

    def _analyze_by_rules(self, user_request: str) -> CreativeBrief:
        return CreativeBrief(
            genre=self._extract_genre(user_request),
            platform=self._extract_platform(user_request),
            episode_count=self._extract_episode_count(user_request),
            episode_duration_minutes=self._extract_duration(user_request),
            tone=self._extract_tone(user_request),
            style_keywords=self._extract_style_keywords(user_request),
            story_seed=user_request.strip() or None,
        )

    def _extract_genre(self, text: str) -> str | None:
        explicit = re.search(r"题材\s*[:：]\s*([^。；;，,\n]+)", text)
        if explicit:
            genre = re.sub(r"(?:短剧)?题材$", "", explicit.group(1).strip()).strip()
            if genre:
                return genre

        for keyword in (
            "都市逆袭",
            "古装甜宠",
            "悬疑",
            "霸总",
            "家庭伦理",
            "职场",
            "复仇",
            "甜宠",
            "穿越",
            "重生",
        ):
            if keyword in text:
                return keyword
        return None

    def _extract_platform(self, text: str) -> str | None:
        for platform in ("抖音", "快手", "小红书", "视频号", "B站", "TikTok"):
            if platform in text:
                return platform
        return None

    def _extract_episode_count(self, text: str) -> int | None:
        match = re.search(r"(\d+)\s*集", text)
        return int(match.group(1)) if match else None

    def _extract_duration(self, text: str) -> float | None:
        minute_match = re.search(r"(\d+(?:\.\d+)?)\s*分钟", text)
        if minute_match:
            return float(minute_match.group(1))
        second_match = re.search(r"(\d+)\s*秒", text)
        return round(int(second_match.group(1)) / 60, 2) if second_match else None

    def _extract_tone(self, text: str) -> str | None:
        hits = [
            keyword
            for keyword in ("强爽点", "快节奏", "轻喜剧", "虐恋", "高甜", "高燃", "暗黑", "治愈")
            if keyword in text
        ]
        return "、".join(hits) if hits else None

    def _extract_style_keywords(self, text: str) -> list[str]:
        return [
            keyword
            for keyword in (
                "强爽点",
                "快节奏",
                "反转",
                "悬念",
                "高甜",
                "轻喜剧",
                "现实主义",
                "电影感",
                "日式青春",
                "赛璐璐",
                "二次元动画",
                "皮克斯",
                "3D动画",
                "毛毡风",
                "剪纸风",
                "像素风",
                "水墨",
                "赛博朋克",
                "80年代港片",
                "港风",
                "王家卫",
                "大卫·林奇",
                "大卫林奇",
                "大卫·拉夏佩尔",
                "大卫拉夏佩尔",
                "MV风",
                "悬疑惊悚",
            )
            if keyword in text
        ]


def _llm_enabled() -> bool:
    return llm_enabled()


def analyze_brief(user_request: str) -> BriefAnalysisResult:
    return BriefAgent().analyze(user_request)
