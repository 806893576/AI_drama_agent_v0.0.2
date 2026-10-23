"""功能：Prompt 加载器，负责读取 YAML 提示词并按 Agent、场景和版本组装。"""

# 作用：定义一个 Prompt 文件加载后的结构。
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


"""
后续所有 Prompt 文件建议统一格式：
    id: writer.story_bible
    name: Story Bible Generator
    description: Generate story bible from creative brief.
    version: 1
    system: |
        你是专业短剧世界观架构师。
    user: |
    请根据以下创作简报生成 Story Bible：
        {{ creative_brief }}
    output_format: json
    variables:
        - creative_brief
"""
class PromptTemplate(BaseModel):
    id: str
    name: str
    description: str | None = None
    version: int = 1
    system: str
    user: str
    output_format: Literal["text", "json"] = "text"
    variables: list[str] = Field(default_factory=list)


"""
把：
    请根据 {{ creative_brief }} 生成 Story Bible
渲染成：
    请根据 {"genre": "都市逆袭"} 生成 Story Bible
说明：
    这里先用简单替换，不引入 Jinja2。等后续 Prompt 复杂了，再考虑模板引擎。
"""
def render_text(template: str, variables: dict[str, Any]) -> str:
    rendered = template

    for key, value in variables.items():
        rendered = rendered.replace("{{ " + key + " }}", str(value))
        rendered = rendered.replace("{{" + key + "}}", str(value))

    return rendered


"""
你后续可以这样用：
    loader = PromptLoader()
    template = loader.load("writer/story_bible.yaml")
    messages = loader.render(template, {"creative_brief": brief_json})
返回：
    {
        "system": "...",
        "user": "..."
    }
"""
class PromptLoader:
    def __init__(self, root_dir: str | Path = "prompts") -> None:
        self.root_dir = Path(root_dir)

    def load(self, relative_path: str | Path) -> PromptTemplate:
        path = self.root_dir / relative_path
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Prompt file must contain a YAML object: {path}")

        return PromptTemplate(**data)

    def render(self, template: PromptTemplate, variables: dict[str, Any]) -> dict[str, str]:
        missing = [name for name in template.variables if name not in variables]
        if missing:
            raise ValueError(f"Missing prompt variables: {missing}")

        return {
            "system": render_text(template.system, variables),
            "user": render_text(template.user, variables),
        }