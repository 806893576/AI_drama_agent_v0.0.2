# 关联生成与拆分保存策略

本项目不再对所有强关联节点一律使用“包生成”。不同阶段采用不同策略：

- Writer 前半段：使用逐层递进生成，保证故事因果链、人物系统、分集切割之间有清晰依赖。
- Director / AV 阶段：继续使用“包生成节点 + 拆分保存节点”，因为这些节点围绕同一批 scene_id / shot_id 协同设计。
- 所有阶段：送入 LLM 前都要先提取必要字段，再渲染为自然语言创作上下文。

## Writer 顺序生成

节点链路：

```text
story_bible
-> story_synopsis
-> character_bible
-> episode_outline
-> episode_script
-> dialogue_polish
-> script_package
```

职责划分：

- `story_bible`：保存稳定设定边界，如标题、完整设定摘要、主题、世界规则、核心冲突、时间线规则和不可变事实。
- `story_synopsis`：把 Story Bible 转成完整故事因果链，说明故事从开始到结束发生什么。
- `character_bible`：基于 Story Bible + Story Synopsis，识别完成整个故事所必需的人物和人物关系。
- `episode_outline`：基于 Story Bible + Story Synopsis + Character Bible，把完整故事和人物系统切成具体集数。

Writer 输入上下文：

- `story_synopsis` 接收自然语言化的 `creative_brief` 和 `story_bible`。
- `character_bible` 接收由 `story_bible` 和 `story_synopsis` 组合成的上游创作上下文。
- `episode_outline` 接收自然语言化的 `creative_brief`、`story_bible`、`story_synopsis` 和轻量 `character_bible`。
- 上下文渲染统一由 `services.llm.context` 负责，节点不直接拼接大段 JSON。

保存结构：

- `story_bible`、`story_synopsis`、`character_bible`、`episode_outline` 分别保存为独立 artifact。
- `writer_package` 只保存 artifact 引用、关键摘要和 ID 索引，避免重复长文本。

## Director 规划包

节点链路：

```text
director_planning_bundle
-> scene_breakdown
-> shot_design
-> performance
-> emotional_rhythm
-> director_package
```

`director_planning_bundle` 一次生成：

- `scene_breakdowns`
- `shot_designs`
- `performance_direction`
- `emotional_rhythm`

LLM 输入：

- 压缩后的 `episode_scripts`
- 只保留 episode_id、scene_id、location、characters、action、情绪目的、剧情推进、关键道具和少量对白样本

保存结构：

- 完整 bundle 保存为 `director_planning_bundle`
- 场景和分镜分别保存为独立 artifact
- 表演和情绪节奏继续保留在 state 和 director package 中

## 镜头视听规划包

节点链路：

```text
shot_av_planning_bundle
-> shot_intent
-> camera
-> lighting
-> sound
-> vfx
-> av_package
```

`shot_av_planning_bundle` 一次生成：

- `shot_intent`
- `camera_plan`
- `lighting_plan`
- `sound_plan`
- `vfx_plan`

LLM 输入：

- 压缩后的 `scene_breakdowns`
- 压缩后的 `shot_designs`
- 视听方案必须以已有 `shot_id` 为 key，避免模型重新发明镜头 ID

保存结构：

- 完整 bundle 保存为 `shot_av_planning_bundle`
- 五个子产物分别保存为独立 artifact
- `audiovisual_package` 主要保存 artifact 引用、shot_id 索引和数量统计，减少重复长文本

## 输入压缩原则

- 给创作节点：传必要设定和约束，不传完整运行状态。
- 给人物节点：传完整故事因果链，但不传导演、视听、美术等无关产物。
- 给分集节点：传人物 ID、角色功能、目标、动机和关系变化方向，不传完整外貌、资产、Prompt。
- 给导演节点：传场景动作、人物、情绪、关键道具和少量对白样本。
- 给视听节点：传 scene/shot 索引、视觉重点和情绪状态。
- 给审核节点：传摘要、ID 列表、关键剧情推进和 prompt 文本，不传完整 artifact。
- 给美术节点：传角色视觉关键词、场景索引、镜头意图和必要光影摘要。
