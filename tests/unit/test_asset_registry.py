from domain.assets.asset_registry import (
    AssetRegistry,
    CharacterAsset,
    PromptAsset,
    SceneAsset,
    ShotAsset,
)
from services.storage.asset_store import AssetRegistryStore


def test_asset_registry_can_upsert_and_query_assets() -> None:
    registry = AssetRegistry(registry_id="asset_registry_v001", job_id="job_001")

    character = CharacterAsset(
        asset_id="char_001",
        name="林夏",
        role_type="protagonist",
        voice_style="克制、锋利",
    )

    scene = SceneAsset(
        asset_id="scene_001",
        episode_id="ep_001",
        location_id="loc_office",
        character_ids=["char_001"],
    )

    registry.upsert_character(character)
    registry.upsert_scene(scene)

    assert registry.has_asset("char_001")
    assert registry.has_asset("scene_001")
    assert registry.get_asset("char_001").name == "林夏"


def test_asset_registry_supports_shot_and_prompt_refs() -> None:
    registry = AssetRegistry(registry_id="asset_registry_v001", job_id="job_001")

    shot = ShotAsset(
        asset_id="shot_001",
        scene_id="scene_001",
        shot_order=1,
        character_ids=["char_001"],
    )

    prompt = PromptAsset(
        asset_id="prompt_001",
        intended_use="character_reference",
        prompt="都市职场女性，冷静克制，黑色西装。",
        character_ids=["char_001"],
        shot_id="shot_001",
    )

    registry.upsert_shot(shot)
    registry.upsert_prompt(prompt)

    assert registry.shots["shot_001"].scene_id == "scene_001"
    assert registry.prompts["prompt_001"].shot_id == "shot_001"


def test_asset_registry_store_save_and_load(tmp_path) -> None:
    store = AssetRegistryStore(root_dir=tmp_path)
    registry = AssetRegistry(registry_id="asset_registry_v001", job_id="job_001")

    registry.upsert_character(
        CharacterAsset(
            asset_id="char_001",
            name="林夏",
            role_type="protagonist",
            voice_style="短句、克制",
        )
    )

    path = store.save(registry)

    assert path.exists()
    assert store.exists("job_001")

    loaded = store.load("job_001")

    assert loaded.registry_id == "asset_registry_v001"
    assert loaded.characters["char_001"].name == "林夏"