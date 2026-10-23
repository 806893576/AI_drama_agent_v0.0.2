from domain.art.image_prompts import (
    ArtAssetPromptLibrary,
    ArtPromptPackage,
    CharacterAssetPrompt,
    PropAssetPrompt,
    SceneAssetPrompt,
    ShotPromptPlan,
)
from domain.directing.shot_design import ShotDesign
from graph.nodes.final_output_node import build_final_generation_sections


def test_build_final_generation_sections_uses_compact_string_lists() -> None:
    art_package = ArtPromptPackage(
        art_prompt_package_id="art_prompt_package_v001",
        style_profile="赛璐璐青春动画风格",
        asset_prompts=ArtAssetPromptLibrary(
            character_assets=[
                CharacterAssetPrompt(
                    asset_id="char_lin_base",
                    character_name="林知夏",
                    variant="base",
                    used_in_shot_ids=["EP_001_SC_001_shot_01"],
                    prompt="林知夏基础角色设定图提示词",
                ),
                CharacterAssetPrompt(
                    asset_id="char_zhou_suit",
                    character_name="周明远",
                    variant="商务正装",
                    used_in_shot_ids=["EP_001_SC_001_shot_01"],
                    prompt="周明远商务正装设定图提示词",
                ),
            ],
            scene_assets=[
                SceneAssetPrompt(
                    asset_id="scene_company_lobby",
                    scene_name="公司前台",
                    scene_id="EP_001_SC_001",
                    used_in_shot_ids=["EP_001_SC_001_shot_01"],
                    prompt="公司前台场景图提示词",
                )
            ],
            prop_assets=[
                PropAssetPrompt(
                    asset_id="prop_suitcase",
                    prop_name="银色行李箱",
                    used_in_scene_ids=["EP_001_SC_001"],
                    used_in_shot_ids=["EP_001_SC_001_shot_01"],
                    prompt="银色行李箱道具图提示词",
                )
            ],
        ),
        shot_prompt_plan=[
            ShotPromptPlan(
                shot_id="EP_001_SC_001_shot_01",
                scene_id="EP_001_SC_001",
                scene_asset_id="scene_company_lobby",
                character_asset_ids=["char_lin_base", "char_zhou_suit"],
                prop_asset_ids=["prop_suitcase"],
                shot_reference_prompt="分镜参考图提示词",
            )
        ],
    )
    enhanced_shot = ShotDesign(
        shot_id="EP_001_SC_001_shot_01",
        scene_id="EP_001_SC_001",
        shot_number=1,
        shot_size="中景",
        composition="前后景构图",
        shot_content="林知夏拖着银色行李箱进入公司前台。",
        camera_position_movement="轻微跟拍推进",
        duration_seconds=6,
        continuity="承接上一镜头的人物动作和道具位置。",
    )

    result = build_final_generation_sections(
        {
            "art_prompt_package": art_package,
            "audiovisual_enhanced_shot_list": [enhanced_shot],
        }
    )

    assert result["art_package"] == {
        "style_profile": "赛璐璐青春动画风格",
        "character_assets": [
            {
                "character_name": "林知夏",
                "variant": "base",
                "prompt": "林知夏基础角色设定图提示词",
            },
            {
                "character_name": "周明远",
                "variant": "商务正装",
                "prompt": "周明远商务正装设定图提示词",
            },
        ],
        "scene_assets": [
            {
                "scene": ["EP_001_SC_001_公司前台"],
                "prompt": "公司前台场景图提示词",
            }
        ],
        "prop_assets": [
            {
                "prop_name": "银色行李箱",
                "used_in_scene_ids": ["EP_001_SC_001"],
                "prompt": "银色行李箱道具图提示词",
            }
        ],
    }
    assert result["audiovisual_enhanced_shot_list"] == [
        {
            "shot_id": "EP_001_SC_001_shot_01",
            "scene": ["EP_001_SC_001_公司前台"],
            "shot_number": 1,
            "characters": ["林知夏_base", "周明远_商务正装"],
            "props": ["银色行李箱"],
            "shot_content": "林知夏拖着银色行李箱进入公司前台。",
            "continuity": "承接上一镜头的人物动作和道具位置。",
        }
    ]


def test_build_final_generation_sections_accepts_checkpoint_dicts() -> None:
    state = {
        "art_prompt_package": {
            "style_profile": "毛毡风",
            "asset_prompts": {
                "character_assets": [
                    {
                        "asset_id": "char_a",
                        "character_name": "阿晴",
                        "variant": "雨衣",
                        "used_in_shot_ids": ["shot_01"],
                        "prompt": "毛毡角色提示词",
                    }
                ],
                "scene_assets": [
                    {
                        "asset_id": "scene_a",
                        "scene_id": "SC_001",
                        "scene_name": "雨夜车站",
                        "prompt": "毛毡车站提示词",
                    }
                ],
                "prop_assets": [
                    {
                        "asset_id": "prop_a",
                        "prop_name": "红雨伞",
                        "used_in_scene_ids": ["SC_001"],
                        "used_in_shot_ids": ["shot_01"],
                        "prompt": "毛毡雨伞提示词",
                    }
                ],
            },
            "shot_prompt_plan": [],
        },
        "audiovisual_enhanced_shot_list": [
            {
                "shot_id": "shot_01",
                "scene_id": "SC_001",
                "shot_number": 1,
                "shot_content": "阿晴撑着红雨伞等车。",
                "continuity": None,
            }
        ],
    }

    result = build_final_generation_sections(state)
    shot = result["audiovisual_enhanced_shot_list"][0]

    assert shot["scene"] == ["SC_001_雨夜车站"]
    assert shot["characters"] == ["阿晴_雨衣"]
    assert shot["props"] == ["红雨伞"]
