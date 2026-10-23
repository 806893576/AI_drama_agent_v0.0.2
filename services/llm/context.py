"""LLM 创作上下文渲染工具。

本模块负责把 Graph State / Artifact Store 中的结构化产物，转换成更适合 LLM 阅读的
自然语言创作上下文。节点仍然使用 Pydantic 模型保存数据，但在送入下一个 LLM 前，
优先给模型看“标题、摘要、规则、转折、人物关系”等人类可读文本，降低模型理解成本。
"""

from __future__ import annotations

from typing import Any


def render_creative_context(*artifacts: Any, title: str | None = None) -> str:
    """组合多个产物为一段自然语言上下文。

    节点侧可以传入 Pydantic 模型或 dict；这里会按常见 artifact 字段自动选择渲染器。
    """

    sections = [_render_artifact(item) for item in artifacts if item is not None]
    body = "\n\n".join(section for section in sections if section.strip())
    if title:
        return f"【{title}】\n{body}".strip()
    return body.strip()


def render_creative_brief_context(brief: Any) -> str:
    data = _to_dict(brief)
    return _section(
        "创作简报",
        [
            _line("题材类型", _join_non_empty(data.get("genre"), data.get("sub_genre"))),
            _line("目标平台", data.get("platform")),
            _line("目标受众", data.get("audience")),
            _line("集数", data.get("episode_count")),
            _line("单集时长", _format_duration(data.get("episode_duration_minutes"))),
            _line("风格基调", data.get("tone")),
            _list("风格关键词", data.get("style_keywords")),
            _line("故事种子", data.get("story_seed")),
            _list("约束条件", data.get("constraints")),
            _list("禁用元素", data.get("forbidden_elements")),
        ],
    )


def render_story_bible_context(story_bible: Any) -> str:
    data = _to_dict(story_bible)
    return _section(
        "Story Bible / 故事圣经",
        [
            _line("故事标题", data.get("title")),
            _line("故事摘要", data.get("summary") or data.get("logline")),
            _line("主题表达", data.get("theme")),
            _line("核心冲突", data.get("core_conflict")),
            _list("世界/叙事规则", data.get("world_rules")),
            _list("时间线规则", data.get("timeline_rules")),
            _list("不可改变事实", data.get("immutable_facts")),
        ],
    )


def render_story_synopsis_context(story_synopsis: Any) -> str:
    data = _to_dict(story_synopsis)
    return _section(
        "Story Synopsis / 故事因果链",
        [
            _line("故事前提", data.get("premise")),
            _line("主角目标", data.get("protagonist_goal")),
            _line("主线发展", data.get("main_story_arc")),
            _turning_points(data.get("major_turning_points")),
            _list("主要冲突", data.get("major_conflicts")),
            _list("因果链", data.get("causal_chain")),
            _character_arcs(data.get("character_arcs")),
            _line("最终高潮", data.get("climax")),
            _line("结局收束", data.get("resolution")),
        ],
    )


def render_character_bible_context(character_bible: Any) -> str:
    data = _to_dict(character_bible)
    characters = []
    for item in data.get("characters", []) or []:
        characters.append(
            _join_non_empty(
                f"{item.get('character_id')} {item.get('name')}",
                f"角色功能：{item.get('role') or item.get('role_type')}",
                f"身份：{item.get('identity')}",
                f"目标：{item.get('external_goal')}",
                f"动机：{item.get('motivation')}",
                f"声口：{item.get('voice_style')}",
                f"弧光：{item.get('character_arc')}",
                sep="；",
            )
        )

    relationships = []
    for item in data.get("relationships", []) or []:
        relationships.append(
            _join_non_empty(
                f"{item.get('source_character_id')} -> {item.get('target_character_id')}",
                f"关系：{item.get('type') or item.get('relationship_type')}",
                item.get("description"),
                f"变化：{item.get('change_arc')}",
                sep="；",
            )
        )

    return _section(
        "Character Bible / 人物系统",
        [
            _list("核心人物", characters),
            _list("人物关系", relationships),
            _groups(data.get("character_groups")),
        ],
    )


def render_episode_outline_context(outline_package: Any) -> str:
    data = _to_dict(outline_package)
    episodes = []
    for item in data.get("episodes", []) or []:
        episodes.append(
            _join_non_empty(
                (
                    f"第{item.get('episode_number')}集"
                    f"《{item.get('title') or item.get('episode_id')}》"
                ),
                f"定位：{item.get('episode_positioning')}",
                f"开场：{item.get('opening_hook')}",
                f"冲突：{item.get('core_conflict')}",
                f"关键事件：{_inline_list(item.get('key_events'))}",
                f"结尾：{item.get('ending_and_cliffhanger')}",
                sep="；",
            )
        )
    return _section("Episode Outline / 分集大纲", [_list("分集", episodes)])


def render_episode_scripts_context(episode_scripts: Any, *, scene_limit: int = 24) -> str:
    scripts = _to_list(episode_scripts)
    lines: list[str] = []
    seen = 0
    for script in scripts:
        script_data = _to_dict(script)
        episode = script_data["episode"]
        for scene in script_data.get("scenes", []) or []:
            if seen >= scene_limit:
                lines.append("后续场景已省略，完整内容请从 Artifact Store 读取。")
                return _section("Episode Scripts / 单集剧本摘要", [_list("场景", lines)])
            seen += 1
            lines.append(
                _join_non_empty(
                    f"第{episode.get('episode_number')}集",
                    f"标题：{episode.get('episode_title')}",
                    f"场次：{scene.get('scene_number')}",
                    f"景别属性：{scene.get('interior_exterior')}",
                    f"地点：{scene.get('location')}",
                    f"时间：{scene.get('time')}",
                    f"衔接：{scene.get('continuity')}",
                    f"正文：{_truncate(scene.get('script_text') or '', 260)}",
                    sep="；",
                )
            )
    return _section("Episode Scripts / 单集剧本摘要", [_list("场景", lines)])


def _render_artifact(value: Any) -> str:
    data = _to_dict(value)
    if "story_bible_id" in data:
        return render_story_bible_context(data)
    if "story_synopsis_id" in data:
        return render_story_synopsis_context(data)
    if "character_bible_id" in data:
        return render_character_bible_context(data)
    if "outline_package_id" in data:
        return render_episode_outline_context(data)
    if any(key in data for key in ("genre", "platform", "story_seed")):
        return render_creative_brief_context(data)
    if isinstance(value, list):
        return render_episode_scripts_context(value)
    return _section("上下文", [str(value)])


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return value
    return {}


def _to_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _section(title: str, lines: list[str | None]) -> str:
    content = "\n".join(line for line in lines if line)
    return f"【{title}】\n{content}" if content else f"【{title}】"


def _line(label: str, value: Any) -> str | None:
    if value is None or value == "" or value == []:
        return None
    return f"{label}：{value}"


def _list(label: str, values: Any) -> str | None:
    if not values:
        return None
    if not isinstance(values, list):
        return _line(label, values)
    items = [str(item) for item in values if item is not None and str(item).strip()]
    if not items:
        return None
    return f"{label}：\n" + "\n".join(
        f"{index}. {item}" for index, item in enumerate(items, start=1)
    )


def _turning_points(values: Any) -> str | None:
    items = []
    for item in values or []:
        point = _to_dict(item)
        items.append(
            _join_non_empty(
                point.get("title") or point.get("turning_point_id"),
                point.get("description"),
                f"作用：{point.get('story_effect')}",
                sep="；",
            )
        )
    return _list("关键转折", items)


def _character_arcs(values: Any) -> str | None:
    items = []
    for item in values or []:
        arc = _to_dict(item)
        items.append(_join_non_empty(arc.get("character_role"), arc.get("arc"), sep="："))
    return _list("人物变化", items)


def _groups(values: Any) -> str | None:
    items = []
    for item in values or []:
        group = _to_dict(item)
        items.append(
            _join_non_empty(
                group.get("group_id"),
                group.get("name"),
                group.get("type"),
                f"成员：{_inline_list(group.get('members'))}",
                sep="；",
            )
        )
    return _list("人物分组", items)


def _inline_list(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, list):
        return "、".join(str(item) for item in values if item is not None)
    return str(values)


def _join_non_empty(*values: Any, sep: str = " / ") -> str:
    return sep.join(str(value) for value in values if value is not None and str(value).strip())


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _format_duration(value: Any) -> str | None:
    if value is None:
        return None
    return f"{value} 分钟"
