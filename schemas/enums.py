"""集中定义全项目共享枚举，避免后续代码里到处写散乱字符串。
Core enumerations shared by the drama agent platform."""

from enum import Enum


# StageId 表示整个任务当前处于哪个大阶段。后续 DramaGraphState.current_stage 会用它。
class StageId(str, Enum):
    INPUT = "input"
    BRIEF = "brief"
    PRODUCER = "producer"
    WRITER = "writer"
    REVIEW = "review"
    REPAIR = "repair"
    DIRECTOR = "director"
    AUDIOVISUAL = "audiovisual"
    ART = "art"
    ASSET = "asset"
    SAFETY = "safety"
    FINAL = "final"


# 作用：固定 LangGraph 节点 ID 和局部返工目标。
"""
后续 RepairPlan.target_node 必须从这些值里选择。例如：
    target_node = NodeId.WRITER_EPISODE_SCRIPT
不要写：
    target_node = "重写第三集剧本"
"""
class NodeId(str, Enum):
    INPUT_SAFETY = "input_safety"
    INPUT_GATE = "input_gate"
    INPUT_REWRITE = "input_rewrite"
    REJECT_END = "reject_end"

    BRIEF_AGENT = "brief_agent"
    BRIEF_GATE = "brief_gate"
    STYLE_GUIDE = "style_guide"
    HUMAN_CONFIRM = "human_confirm"
    HUMAN_BRIEF_CONFIRM = "human_brief_confirm"
    HUMAN_STYLE_CONFIRM = "human_style_confirm"
    HUMAN_EPISODE_OUTLINE_CONFIRM = "human_episode_outline_confirm"

    PRODUCER_ROUTER = "producer_router"
    LOCAL_REPAIR_ROUTER = "local_repair_router"

    WRITER_STORY_BIBLE = "writer.story_bible"
    WRITER_STORY_SYNOPSIS = "writer.story_synopsis"
    WRITER_CHARACTER_BIBLE = "writer.character_bible"
    WRITER_EPISODE_OUTLINE = "writer.episode_outline"
    WRITER_EPISODE_SCRIPT = "writer.episode_script"
    WRITER_DIALOGUE_POLISH = "writer.dialogue_polish"
    WRITER_SCRIPT_PACKAGE = "writer.script_package"

    SCRIPT_REVIEWER = "script_reviewer"
    QUALITY_SCORING = "quality_scoring"
    SCRIPT_SAFETY = "script_safety"
    TEXT_CONTINUITY = "text_continuity"
    REPAIR_PLANNER = "repair_planner"

    DIRECTOR_SCENE_BREAKDOWN = "director.scene_breakdown"
    DIRECTOR_SHOT_DESIGN = "director.shot_design"
    DIRECTOR_PERFORMANCE = "director.performance"
    DIRECTOR_PACKAGE = "director.package"

    AV_ENHANCEMENT = "av.enhancement"
    AV_PACKAGE = "av.package"

    SHOT_AV_SAFETY = "shot_av_safety"
    ART_AGENT = "art_agent"
    PROMPT_SAFETY = "prompt_safety"
    ASSET_MANAGER = "asset_manager"
    PRODUCTION_CONTINUITY = "production_continuity"

    FINAL_SAFETY = "final_safety"
    FINAL_ACCEPTANCE = "final_acceptance"
    FINAL_OUTPUT = "final_output"


# 作用：统一 Artifact Store 中长文本产物的类型。
"""
后续保存产物时可以这样写：
    ArtifactType.WRITER_PACKAGE
而不是混用 "script_package"、"writerPackage"、"writer_package"。
"""
class ArtifactType(str, Enum):
    CREATIVE_BRIEF = "creative_brief"
    BRIEF_VALIDATION = "brief_validation"
    STYLE_GUIDE = "style_guide"

    STORY_BIBLE = "story_bible"
    STORY_SYNOPSIS = "story_synopsis"
    CHARACTER_BIBLE = "character_bible"
    EPISODE_OUTLINE = "episode_outline"
    EPISODE_SCRIPT = "episode_script"
    DIALOGUE_POLISH = "dialogue_polish"
    WRITER_PACKAGE = "writer_package"

    SCRIPT_REVIEW = "script_review"
    QUALITY_SCORE = "quality_score"
    SAFETY_REVIEW = "safety_review"
    CONTINUITY_REVIEW = "continuity_review"
    REPAIR_PLAN = "repair_plan"

    SCENE_BREAKDOWN = "scene_breakdown"
    SHOT_LIST = "shot_list"
    PERFORMANCE_DIRECTION = "performance_direction"
    AUDIOVISUAL_ENHANCED_SHOT_LIST = "audiovisual_enhanced_shot_list"
    DIRECTOR_PACKAGE = "director_package"

    AUDIOVISUAL_PACKAGE = "audiovisual_package"

    ART_PACKAGE = "art_package"
    IMAGE_PROMPT = "image_prompt"
    ASSET_REGISTRY = "asset_registry"
    FINAL_PACKAGE = "final_package"


# 定义审核、风险、安全和返工枚举
# 作用：给审核报告、质量评分、安全审核和返工规划提供统一字段。
class ReviewType(str, Enum):
    SCRIPT = "script"
    TEXT_CONTINUITY = "text_continuity"
    PRODUCTION_CONTINUITY = "production_continuity"
    SAFETY = "safety"
    QUALITY = "quality"
    FINAL_ACCEPTANCE = "final_acceptance"

class IssueType(str, Enum):
    BRIEF_INCOMPLETE = "brief_incomplete"
    STORY_LOGIC = "story_logic"
    CHARACTER_MOTIVATION = "character_motivation"
    CHARACTER_VOICE = "character_voice"
    PACING = "pacing"
    HOOK = "hook"
    REVERSAL = "reversal"
    PLATFORM_FIT = "platform_fit"
    SHOOTABILITY = "shootability"
    TEXT_CONTINUITY = "text_continuity"
    ASSET_CONTINUITY = "asset_continuity"
    SHOT_DESIGN = "shot_design"
    CAMERA_DESIGN = "camera_design"
    SOUND_DESIGN = "sound_design"
    VFX_DESIGN = "vfx_design"
    ART_DIRECTION = "art_direction"
    PROMPT_QUALITY = "prompt_quality"
    SAFETY_RISK = "safety_risk"
    COPYRIGHT_RISK = "copyright_risk"

class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SafetyLayer(str, Enum):
    INPUT = "safety_l1_input"
    SCRIPT_TEXT = "safety_l2_script_text"
    SHOT_AV = "safety_l3a_shot_av"
    VISUAL_PROMPT = "safety_l3b_visual_prompt"
    FINAL = "safety_l4_final"

class RepairScope(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    NODE = "node"
    SUBGRAPH = "subgraph"
    STAGE = "stage"
    FULL_RESTART = "full_restart"


# 定义决策与运行状态枚举
# 作用：让 Gate、Producer Router、事件流输出结构化状态。
"""后续 Producer Router 可以输出：
{
    "mode": ProducerMode.REPAIR,
    "status": DecisionStatus.NEEDS_REPAIR,
    "next_node": NodeId.LOCAL_REPAIR_ROUTER,
}"""
class DecisionStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REPAIR = "needs_repair"
    NEEDS_HUMAN_CONFIRM = "needs_human_confirm"
    NEEDS_USER_INPUT = "needs_user_input"
    REJECTED = "rejected"
    TERMINATED = "terminated"
    COMPLETED = "completed"

class ProducerMode(str, Enum):
    NORMAL = "normal"
    REPAIR = "repair"
    HUMAN_CONFIRM = "human_confirm"
    FINAL_REVIEW = "final_review"
    END = "end"

class EventStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_FOR_USER = "waiting_for_user"


# 作用：让资产类型成为受控枚举，而不是散乱字符串。
"""
后续登记资产时使用：
    AssetType.CHARACTER
    AssetType.SCENE
    AssetType.PROMPT
而不是直接写 "character"、"scene"、"prompt"。
"""
class AssetType(str, Enum):
    CHARACTER = "character"
    SCENE = "scene"
    LOCATION = "location"
    PROP = "prop"
    COSTUME = "costume"
    MAKEUP = "makeup"
    SOUND = "sound"
    MUSIC = "music"
    SHOT = "shot"
    PROMPT = "prompt"
    REFERENCE_IMAGE = "reference_image"
    GENERATED_IMAGE = "generated_image"
    GENERATED_AUDIO = "generated_audio"
    GENERATED_VIDEO = "generated_video"
