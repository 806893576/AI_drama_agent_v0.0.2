# 真实 LLM 接入说明

当前工程支持 OpenAI-compatible Chat Completions API，并已内置 DeepSeek 配置读取。
默认使用 `fake` 客户端；配置真实 Key 后，LangGraph 节点会优先调用真实模型。真实模型请求失败时会暂停任务并返回错误，不会静默写入规则兜底产物。

## DeepSeek 配置

你的 `.env` 可以直接使用 DeepSeek 专用变量：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_STRUCTURED_MODEL=deepseek-chat
DEEPSEEK_REASON_MODEL=deepseek-reasoner
LLM_FORCE_JSON_OBJECT=false
```

可选地显式指定：

```env
LLM_CLIENT=deepseek
```

如果没有配置 `LLM_CLIENT`，但存在有效的 `DEEPSEEK_API_KEY`，工程会自动选择 DeepSeek。
当前所有接入节点都要求模型输出结构化 JSON，因此默认优先使用 `DEEPSEEK_STRUCTURED_MODEL`。

## OpenAI 或其他兼容供应商

```env
LLM_CLIENT=openai
OPENAI_API_KEY=你的 API Key
OPENAI_BASE_URL=https://api.openai.com
OPENAI_MODEL=gpt-4.1-mini
LLM_FORCE_JSON_OBJECT=false
```

`OPENAI_BASE_URL` 可以是根地址，也可以直接带 `/v1`，客户端会自动拼接 Chat Completions 路径。

## 已接入真实 LLM 的模块

- `BriefAgent`：生成 `CreativeBrief`
- Writer Subgraph：
  - `writer.story_bible`
  - `writer.story_synopsis`
  - `writer.character_bible`
  - `writer.episode_outline`
  - `writer.episode_script`
  - `writer.dialogue_polish`
- Director Subgraph：
  - `director.scene_breakdown`
  - `director.shot_design`
  - `director.performance`
  - `director.emotional_rhythm`
  - `director.shot_intent`
- Audiovisual Subgraph：
  - `audiovisual.camera`
  - `audiovisual.lighting`
  - `audiovisual.sound`
  - `audiovisual.vfx`
- Art / Assets：
  - `agents.art_agent`
- Review / Repair：
  - `agents.script_reviewer`
  - `agents.quality_scoring`
  - `agents.safety_reviewer`
  - `agents.continuity_reviewer`
  - `agents.repair_planner`

## Web 入口

`http://127.0.0.1:8000/` 的网页端提交任务时调用 `/api/v1/jobs`，该接口直接调用 `workflows.generation_workflow.run_generation()`。
因此网页端、CLI 和 API 共用同一套 LangGraph 主流程与 LLM 配置。

启动服务：

```powershell
python app.py --serve
```

## 运行策略

1. `LLM_CLIENT=fake` 时使用规则兜底生成器，方便本地开发和单元测试。
2. `LLM_CLIENT=deepseek` 或自动识别到 `DEEPSEEK_API_KEY` 时调用 DeepSeek。
3. `LLM_CLIENT=openai` 时调用 OpenAI-compatible 配置。
4. 如果真实模型接口调用失败，例如网络、SSL、超时或服务端错误，任务会中断并返回 `llm_runtime_error`。
5. 如果模型返回内容无法解析为 JSON，或无法通过 Pydantic 校验，默认会中断当前任务并返回 `llm_format_error`，等待用户确认。
6. 用户确认后，前端会用 `llm_format_mode=auto_repair` 重新运行任务；再次遇到格式错误时，系统会把原始输出、错误信息和目标 schema 发送给 LLM 做一次格式修复。

## 创作上下文渲染

结构化产物在保存时仍使用 Pydantic / JSON，但送入下一个 LLM 前，优先通过
`services.llm.context` 转换成自然语言创作上下文。

核心函数：

- `render_creative_brief_context()`：把 `CreativeBrief` 渲染为题材、平台、集数、风格和故事种子。
- `render_story_bible_context()`：把 `StoryBible` 渲染为标题、摘要、主题、规则和不可变事实。
- `render_story_synopsis_context()`：把 `StorySynopsis` 渲染为前提、主线、转折、因果链和结局。
- `render_character_bible_context()`：把 `CharacterBible` 渲染为核心人物卡和轻量关系卡。
- `render_creative_context()`：组合多个上游产物，形成当前节点所需的完整创作上下文。

这样做的目的：

- 让模型先读懂故事，而不是先处理嵌套 JSON。
- 减少无关字段进入 Prompt，降低 token 消耗。
- 降低复杂 schema 节点，尤其是 `writer.character_bible` 的格式化失败率。
- 保持存储层结构化，同时让 LLM 调用层更接近创作者阅读习惯。

## 结构化输出失败处理

默认请求使用：

```json
{
  "llm_format_mode": "interrupt"
}
```

格式失败时 API 返回：

```json
{
  "human_confirmation_required": true,
  "llm_repair_available": true,
  "llm_format_error": {
    "prompt_id": "writer.story_synopsis",
    "error_message": "JSON 或 Pydantic 校验错误",
    "raw_output": "模型原始输出预览",
    "target_schema": {}
  }
}
```

确认修复后重新提交：

```json
{
  "llm_format_mode": "auto_repair"
}
```

网页端会自动保留同一个 `job_id` 重新运行。若之前已经生成部分 artifact，新运行会按版本规则生成后续版本，例如 `story_bible_v002`。

## 真实模型请求失败处理

网络、SSL、超时或模型服务异常属于请求阶段失败，不属于 JSON 格式修复场景。API 会返回：

```json
{
  "human_confirmation_required": true,
  "llm_retry_available": true,
  "llm_runtime_error": {
    "prompt_id": "writer.story_synopsis",
    "error_message": "[SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC] ..."
  }
}
```

网页端会显示“重试同一任务”和“退出本次任务”。重试会再次调用真实 LLM；退出不会继续消耗 token。

## 调用示例

```powershell
python app.py --request "都市逆袭短剧，平台抖音，12集，每集2分钟，风格强爽点、快节奏，女主被夺走公司后重新夺回主动权。"
```

快速草稿可跳过部分审核节点：

```powershell
python app.py --request "都市逆袭短剧，平台抖音，12集，每集2分钟。" --fast-draft
```
