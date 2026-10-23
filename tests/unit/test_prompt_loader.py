from pathlib import Path

import pytest

from prompts import PromptLoader, PromptRegistry, render_text


def test_render_text_replaces_variables() -> None:
    rendered = render_text(
        "你好，{{ name }}。今天的任务是：{{task}}。",
        {"name": "林夏", "task": "生成短剧大纲"},
    )

    assert rendered == "你好，林夏。今天的任务是：生成短剧大纲。"


def test_prompt_loader_loads_and_renders_yaml(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "prompts"
    template_dir = prompt_dir / "templates"
    template_dir.mkdir(parents=True)

    prompt_file = template_dir / "test_prompt.yaml"
    prompt_file.write_text(
        """
id: test.prompt
name: Test Prompt
description: Prompt used by unit tests.
version: 1
system: |
  你是测试助手。
user: |
  请处理以下输入：
  {{ input_text }}
output_format: text
variables:
  - input_text
""".strip(),
        encoding="utf-8",
    )

    loader = PromptLoader(root_dir=prompt_dir)
    template = loader.load("templates/test_prompt.yaml")

    rendered = loader.render(template, {"input_text": "生成短剧大纲"})

    assert template.id == "test.prompt"
    assert rendered["system"] == "你是测试助手。\n"
    assert "生成短剧大纲" in rendered["user"]


def test_prompt_loader_rejects_missing_variables(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "prompts"
    template_dir = prompt_dir / "templates"
    template_dir.mkdir(parents=True)

    prompt_file = template_dir / "test_prompt.yaml"
    prompt_file.write_text(
        """
id: test.prompt
name: Test Prompt
system: |
  system
user: |
  {{ input_text }}
variables:
  - input_text
""".strip(),
        encoding="utf-8",
    )

    loader = PromptLoader(root_dir=prompt_dir)
    template = loader.load("templates/test_prompt.yaml")

    with pytest.raises(ValueError):
        loader.render(template, {})


def test_prompt_registry_scans_prompt_ids(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "prompts"
    writer_dir = prompt_dir / "writer"
    writer_dir.mkdir(parents=True)

    prompt_file = writer_dir / "story_bible.yaml"
    prompt_file.write_text(
        """
id: writer.story_bible
name: Story Bible
system: |
  system
user: |
  user
output_format: json
variables: []
""".strip(),
        encoding="utf-8",
    )

    registry = PromptRegistry(root_dir=prompt_dir)
    registry.scan()

    assert registry.list_ids() == ["writer.story_bible"]
    assert registry.get("writer.story_bible").output_format == "json"