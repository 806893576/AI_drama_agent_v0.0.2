from domain.brief.schemas import CreativeBrief
from domain.style import CreativeStyleGuide
from services.style import build_creative_style_guide, load_style_presets, match_style_presets


def test_style_presets_load_and_match_visual_and_director_styles() -> None:
    brief = CreativeBrief(
        genre="青春悬疑",
        platform="抖音",
        episode_count=8,
        episode_duration_minutes=2,
        tone="清冷、暧昧、悬念",
        style_keywords=["赛璐璐", "王家卫式", "像素风"],
        story_seed="几个高中生在雨夜车站发现一段失踪录像。",
    )

    presets = match_style_presets(brief, user_request="赛璐璐 + 王家卫式霓虹疏离")
    names = {preset.name for preset in presets}

    assert "赛璐璐动画" in names
    assert "霓虹疏离电影诗" in names


def test_creative_style_guide_uses_string_fields_only() -> None:
    brief = CreativeBrief(
        genre="都市逆袭",
        platform="抖音",
        episode_count=12,
        episode_duration_minutes=2,
        style_keywords=["80年代港片", "港风"],
        story_seed="女主被夺走公司后在雨夜街头重新集结盟友。",
    )

    guide = build_creative_style_guide(brief, user_request="80年代港片风格，复古港风霓虹")
    dumped = guide.model_dump()

    assert isinstance(guide, CreativeStyleGuide)
    assert "80年代港片动势" in guide.matched_presets
    assert "霓虹" in guide.lighting_profile
    assert dumped
    assert all(isinstance(value, str) for value in dumped.values())


def test_style_preset_library_contains_art_and_director_presets() -> None:
    presets = load_style_presets()
    preset_types = {preset.preset_type for preset in presets}

    assert {"art", "director"} <= preset_types
    assert len(presets) >= 12


def test_recommended_style_presets_are_registered() -> None:
    presets = load_style_presets()
    preset_ids = {preset.preset_id for preset in presets}

    assert {
        "low_poly_3d",
        "motion_graphics_vector",
        "rotoscope_animation",
        "ukiyo_e_print",
        "art_deco_luxury",
        "brutalist_urban",
        "pop_art_comic",
        "vaporwave_synthwave",
        "german_expressionism",
        "film_noir_classic",
        "french_new_wave",
        "soviet_montage",
        "screenlife_desktop",
        "found_footage",
    } <= preset_ids


def test_new_style_presets_match_common_chinese_aliases() -> None:
    brief = CreativeBrief(
        genre="都市奇幻",
        platform="抖音",
        episode_count=1,
        episode_duration_minutes=2,
        style_keywords=["浮世绘", "桌面电影", "伪纪录"],
        story_seed="女主在直播后台发现一段被删除的偷拍视频。",
    )

    presets = match_style_presets(brief, user_request="浮世绘视觉，桌面电影叙事，伪纪录手持质感")
    names = {preset.name for preset in presets}

    assert "浮世绘版画" in names
    assert "桌面屏幕电影" in names
    assert "伪纪录发现影像" in names
