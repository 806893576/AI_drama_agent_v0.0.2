"""编剧子图路由占位。

用于支持正常顺序生成和局部返工路由，例如只重写某一集、某几场戏或只执行对白润色。
"""

# 作用：先定义子图内节点名常量，后续返工重入也会用这些名字。
# 避免在 graph.py 里到处写裸字符串。
STORY_BIBLE = "story_bible"
STORY_SYNOPSIS = "story_synopsis"
CHARACTER_BIBLE = "character_bible"
EPISODE_OUTLINE = "episode_outline"
HUMAN_EPISODE_OUTLINE_CONFIRM = "human_episode_outline_confirm"
EPISODE_SCRIPT = "episode_script"
DIALOGUE_POLISH = "dialogue_polish"
SCRIPT_PACKAGE = "script_package"


def route_after_episode_outline(state: dict) -> str:
    from graph.edges import _should_pause_for_confirmation

    if _should_pause_for_confirmation(state, "episode_outline"):
        return HUMAN_EPISODE_OUTLINE_CONFIRM
    return EPISODE_SCRIPT
