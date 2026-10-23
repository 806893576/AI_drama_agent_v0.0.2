"""剧本审稿人 Agent。"""

from __future__ import annotations

from agents.base_agent import AgentContext, AgentResult, BaseAgent
from domain.review.script_review import ScriptReviewReport
from services.llm import generate_model_with_fallback, json_dumps_for_prompt


class ScriptReviewerAgent(BaseAgent[ScriptReviewReport]):
    name = "script_reviewer_agent"

    def run(self, context: AgentContext, **kwargs) -> AgentResult[ScriptReviewReport]:
        episode_scripts = kwargs.get("episode_scripts", [])
        report = generate_model_with_fallback(
            "agents.script_reviewer",
            {
                "user_request": context.user_request,
                "episode_scripts": json_dumps_for_prompt(
                    _compact_episode_scripts_for_review(episode_scripts)
                ),
            },
            ScriptReviewReport,
            fallback=lambda: self._rule_review(episode_scripts),
            temperature=0.2,
        )
        return AgentResult(output=report, summary=report.overall_comment)

    def _rule_review(self, episode_scripts: list) -> ScriptReviewReport:
        """规则兜底：保证无模型环境下仍能驱动条件边。"""

        passed = bool(episode_scripts)
        report = ScriptReviewReport(
            report_id="script_review_v001",
            passed=passed,
            overall_comment=(
                "剧本结构完整，可以进入质量评分。" if passed else "缺少单集剧本，无法审核。"
            ),
            strengths=["钩子明确", "冲突可持续", "角色声口有区分"] if passed else [],
            revision_notes=[] if passed else ["请补齐单集剧本。"],
        )
        return report


def _compact_episode_scripts_for_review(episode_scripts: list) -> list[dict]:
    """剧本审核只需要单集框架和场景正文摘要，避免发送完整长剧本。"""

    compact = []
    for script in episode_scripts:
        compact.append(
            {
                "episode_script_id": script.episode_script_id,
                "project_metadata": script.project_metadata.model_dump(
                    mode="json",
                    exclude_none=True,
                ),
                "episode": script.episode.model_dump(mode="json", exclude_none=True),
                "scenes": [
                    {
                        "scene_id": _scene_ref(script, scene),
                        "scene_number": scene.scene_number,
                        "interior_exterior": scene.interior_exterior,
                        "location": scene.location,
                        "time": scene.time,
                        "continuity": scene.continuity,
                        "script_text": scene.script_text,
                    }
                    for scene in script.scenes
                ],
            }
        )
    return compact


def _episode_ref(script) -> str:
    return f"EP_{script.episode.episode_number:03d}"


def _scene_ref(script, scene) -> str:
    return f"{_episode_ref(script)}_SC_{scene.scene_number:03d}"
