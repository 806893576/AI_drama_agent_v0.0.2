"""Creative style guide models.

All fields are strings by design so prompts can consume a stable, flat profile
without list/object shape drift from LLM output.
"""

from pydantic import BaseModel


class CreativeStyleGuide(BaseModel):
    style_guide_id: str = "style_guide_v001"
    style_name: str = "默认短剧制作风格"
    source_keywords: str = ""
    matched_presets: str = ""
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
