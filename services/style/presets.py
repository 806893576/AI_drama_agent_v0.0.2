"""Local style preset loading and deterministic CreativeStyleGuide fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from domain.brief.schemas import CreativeBrief
from domain.style import CreativeStyleGuide


class StylePreset(BaseModel):
    preset_id: str
    preset_type: str
    name: str
    aliases: str = ""
    visual_style_profile: str = ""
    director_style_profile: str = ""
    cinematography_profile: str = ""
    lighting_profile: str = ""
    color_palette: str = ""
    art_direction_profile: str = ""
    render_style: str = ""
    performance_profile: str = ""
    editing_rhythm: str = ""
    sound_profile: str = ""
    vfx_profile: str = ""
    style_do: str = ""
    style_do_not: str = ""
    safety_notes: str = ""


def load_style_presets(root_dir: str | Path = "styles/presets") -> list[StylePreset]:
    root = Path(root_dir)
    if not root.exists():
        return []

    presets: list[StylePreset] = []
    for path in sorted(root.rglob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            presets.append(StylePreset(**{key: str(value or "") for key, value in data.items()}))
    return presets


def match_style_presets(
    brief: CreativeBrief,
    *,
    user_request: str = "",
    presets: list[StylePreset] | None = None,
) -> list[StylePreset]:
    presets = presets if presets is not None else load_style_presets()
    haystack = _brief_style_text(brief, user_request=user_request)
    scored: list[tuple[int, StylePreset]] = []
    for preset in presets:
        score = _match_score(haystack, preset)
        if score > 0:
            scored.append((score, preset))

    scored.sort(key=lambda item: (-item[0], item[1].preset_id))
    selected: list[StylePreset] = []
    type_counts: dict[str, int] = {}
    for _score, preset in scored:
        if len(selected) >= 4:
            break
        # Allow explicit blends such as "日式青春 + 赛璐璐 + 王家卫式",
        # while still preventing one dimension from flooding the whole guide.
        if type_counts.get(preset.preset_type, 0) >= 3:
            continue
        selected.append(preset)
        type_counts[preset.preset_type] = type_counts.get(preset.preset_type, 0) + 1

    return selected or _default_presets(presets)


def build_creative_style_guide(
    brief: CreativeBrief,
    *,
    user_request: str = "",
    presets: list[StylePreset] | None = None,
) -> CreativeStyleGuide:
    matched = match_style_presets(brief, user_request=user_request, presets=presets)
    return _merge_presets(brief, matched, user_request=user_request)


def render_style_presets_for_prompt(presets: list[StylePreset]) -> str:
    if not presets:
        return "未匹配到本地预设。"
    chunks = []
    for preset in presets:
        chunks.append(
            "\n".join(
                [
                    f"预设：{preset.name}",
                    f"类型：{preset.preset_type}",
                    f"别名：{preset.aliases}",
                    f"视觉：{preset.visual_style_profile}",
                    f"导演：{preset.director_style_profile}",
                    f"摄影：{preset.cinematography_profile}",
                    f"光影：{preset.lighting_profile}",
                    f"色彩：{preset.color_palette}",
                    f"美术：{preset.art_direction_profile}",
                    f"渲染：{preset.render_style}",
                    f"表演：{preset.performance_profile}",
                    f"剪辑：{preset.editing_rhythm}",
                    f"声音：{preset.sound_profile}",
                    f"特效：{preset.vfx_profile}",
                    f"必须做：{preset.style_do}",
                    f"不要做：{preset.style_do_not}",
                    f"安全说明：{preset.safety_notes}",
                ]
            ).strip()
        )
    return "\n\n".join(chunks)


def _merge_presets(
    brief: CreativeBrief,
    presets: list[StylePreset],
    *,
    user_request: str,
) -> CreativeStyleGuide:
    source_keywords = _source_keywords(brief, user_request=user_request)
    preset_names = " / ".join(preset.name for preset in presets)
    style_name = f"融合风格：{preset_names}" if preset_names else "默认短剧制作风格"
    return CreativeStyleGuide(
        style_name=style_name,
        source_keywords=source_keywords,
        matched_presets=preset_names,
        visual_style_profile=_merge_field(presets, "visual_style_profile"),
        director_style_profile=_merge_field(presets, "director_style_profile"),
        cinematography_profile=_merge_field(presets, "cinematography_profile"),
        lighting_profile=_merge_field(presets, "lighting_profile"),
        color_palette=_merge_field(presets, "color_palette"),
        art_direction_profile=_merge_field(presets, "art_direction_profile"),
        render_style=_merge_field(presets, "render_style"),
        performance_profile=_merge_field(presets, "performance_profile"),
        editing_rhythm=_merge_field(presets, "editing_rhythm"),
        sound_profile=_merge_field(presets, "sound_profile"),
        vfx_profile=_merge_field(presets, "vfx_profile"),
        style_do=_append_generic_rules(_merge_field(presets, "style_do")),
        style_do_not=_append_generic_limits(_merge_field(presets, "style_do_not")),
        safety_notes=_append_safety_notes(_merge_field(presets, "safety_notes")),
    )


def _merge_field(presets: list[StylePreset], field_name: str) -> str:
    values = []
    seen = set()
    for preset in presets:
        value = str(getattr(preset, field_name, "")).strip()
        if value and value not in seen:
            values.append(f"{preset.name}：{value}")
            seen.add(value)
    return "；".join(values)


def _brief_style_text(brief: CreativeBrief, *, user_request: str) -> str:
    values: list[Any] = [
        user_request,
        brief.genre,
        brief.sub_genre,
        brief.platform,
        brief.audience,
        brief.tone,
        brief.story_seed,
        *brief.style_keywords,
        *brief.constraints,
        *brief.forbidden_elements,
    ]
    return " ".join(str(value).lower() for value in values if value)


def _source_keywords(brief: CreativeBrief, *, user_request: str) -> str:
    values = [
        *brief.style_keywords,
        brief.tone,
        brief.genre,
        brief.sub_genre,
        user_request,
    ]
    return "；".join(str(value) for value in values if value)


def _match_score(haystack: str, preset: StylePreset) -> int:
    needles = [preset.name, preset.preset_id, *preset.aliases.replace("，", ",").split(",")]
    score = 0
    for needle in needles:
        text = needle.strip().lower()
        if text and text in haystack:
            score += 3 if text == preset.name.lower() else 1
    return score


def _default_presets(presets: list[StylePreset]) -> list[StylePreset]:
    defaults = [
        preset
        for preset in presets
        if preset.preset_id in {"cinematic_short_drama", "documentary_realism"}
    ]
    if defaults:
        return defaults
    return presets[:1]


def _append_generic_rules(value: str) -> str:
    generic = (
        "所有风格规则必须服务剧情、人物关系和短剧可拍摄性；"
        "同一项目内角色、场景、镜头、声音和资产必须保持统一。"
    )
    return f"{value}；{generic}" if value else generic


def _append_generic_limits(value: str) -> str:
    generic = (
        "不得让风格改变剧情因果、对白含义、人物行为和叙事结果；"
        "不得在图像或视频提示词中直接要求模仿真实品牌、版权角色或在世创作者。"
    )
    return f"{value}；{generic}" if value else generic


def _append_safety_notes(value: str) -> str:
    generic = (
        "当用户引用品牌、片厂、摄影师或导演时，最终提示词应转译为"
        "色彩、光影、材质、构图、节奏和声音等描述性特征。"
    )
    return f"{value}；{generic}" if value else generic
