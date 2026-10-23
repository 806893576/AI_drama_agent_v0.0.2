# 系统架构设计

## 目标

系统目标是生成一套完整的 AI 短剧制作方案，包括创作简报、Story Bible、人物设定、分集大纲、单集剧本、导演分镜、摄影/灯光/声音/特效方案、美术 Prompt、资产清单、审核报告和最终交付包。

架构采用 LangGraph 主图加子图的方式：主图负责阶段推进和条件路由，子图负责复杂专业阶段，所有模块通过统一状态和产物引用协作。

## 分层

```text
API / Workflow Layer
  调用端到端短剧生成、分集生成、导出等业务流程。

Graph Layer
  组装 LangGraph 主图、节点、条件边、checkpoint 和子图。

Agent Layer
  承载需求分析、制片调度、审稿、一致性、安全、美术、资产、返工规划和质量评分。

Domain Layer
  定义短剧业务对象，例如 CreativeBrief、StoryBible、EpisodeScript、ShotList、ArtPrompt。

State / Artifact Layer
  Graph State 保存轻量运行状态；Artifact Store 保存长文本；Asset Registry 保存资产版本关系。

Services Layer
  封装 LLM、Embedding、Vector、Storage、外部 API 等基础能力。
```

## 核心原则

- Agent 之间不私下传递长文本，统一通过状态引用和产物库读取。
- Producer Agent 是 supervisor/router，不是创作型 Agent。
- 审核失败后先进入 Repair Planner，再进行局部返工。
- 安全审核按对象分级，避免一个通用安全 prompt 审所有内容。
- 资产管理员从编剧阶段开始介入，维护角色、场景、道具、镜头和 Prompt 的稳定 ID。

## MVP 范围

第一阶段建议只实现：输入安全、需求分析、制片调度、编剧子图、剧本审稿、质量评分、返工规划、剧本安全和最终文本输出。

第二阶段扩展：导演子图、视听设计子图、美术组、资产管理员和跨产物一致性审核。

第三阶段完善：多轮局部返工、人机确认、导出、评测集、可观测性和 API。
