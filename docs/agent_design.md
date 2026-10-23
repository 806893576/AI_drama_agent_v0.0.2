# Agent 职责设计

## Producer Agent

定位：Supervisor Router。

职责：

- 判断创作简报是否足够启动。
- 推进当前阶段。
- 根据审核报告选择返工目标。
- 控制最大返工次数。
- 触发人机确认。
- 汇总最终验收。

不负责：生成故事、写台词、设计分镜、写 Prompt。

## Brief Agent

负责将用户输入转为 CreativeBrief，包括题材、类型、平台、受众、集数、单集时长、风格、禁忌点、参考方向和缺失字段。

## Writer Subgraph

负责生成 Story Bible、人物圣经、分集大纲、单集剧本和对白润色结果。它是一个可重入子图，不是单一 Agent。

## Script Reviewer Agent

负责剧本质量审核，关注剧情逻辑、人物动机、节奏、爽点、反转、平台适配度和可拍性。

## Continuity Reviewer Agent

负责两类一致性审核：

- 文本阶段：人物关系、时间线、伏笔、场景和道具连续性。
- 制作阶段：剧本、分镜、视觉资产、声音资产、服装、道具、位置和时间线一致性。

## Safety Reviewer Agent

负责分级安全审核，调用不同 guard 策略检查输入、剧本、镜头、视听设计、视觉 Prompt 和版权/IP 风险。

## Director Subgraph

负责场景拆解、分镜设计、表演调度、情绪节奏和镜头意图。

## Audiovisual Subgraph

负责摄影、灯光、声音和特效设计。

## Art Agent

负责人物形象、场景、服化道、视觉参考和图片生成 Prompt。

## Asset Manager Agent

负责资产注册、版本管理和引用关系维护。它应从 Story Bible 与人物设定阶段就开始记录角色、场景和关键道具。

## Repair Planner Agent

负责把审核失败结果转为局部返工计划，包括问题来源、影响产物、最小返工范围、目标节点和保留不变项。

## Quality Scoring Agent

负责将审核报告量化，输出可供条件边判断的分数和阈值结果。
