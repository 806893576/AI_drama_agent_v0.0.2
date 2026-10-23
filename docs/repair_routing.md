# 返工路由设计

## 核心原则

审核失败后不直接重跑整条流程，而是先进入 Repair Planner，判断最小责任节点和最小修改范围。

## 返工计划字段

```json
{
  "problem": "第 3 集女主行为动机不足",
  "issue_type": "character_motivation",
  "affected_artifacts": ["episode_03_script", "character_bible"],
  "target_node": "writer.episode_script",
  "scope": "partial",
  "keep_unchanged": ["story_bible", "episode_01", "episode_02"],
  "instructions": ["补足女主选择反击的外部压力", "保持结尾反转不变"],
  "max_retries": 2
}
```

## 推荐路由规则

```text
需求缺失
  -> human_confirm -> brief_agent

Story Bible 冲突
  -> writer.story_bible

人物动机问题
  -> writer.character_bible 或 writer.episode_script

分集节奏问题
  -> writer.episode_outline

单集对白问题
  -> writer.dialogue_polish

文本安全风险
  -> writer 对应最小节点

分镜/导演问题
  -> director.shot_design 或 director.performance

视听设计问题
  -> audiovisual.camera / lighting / sound / vfx

美术资产问题
  -> art_agent

Prompt 安全风险
  -> art_agent

资产引用冲突
  -> asset_manager 或责任创作节点
```

## 重试控制

每个目标节点都应记录 retry_count。超过最大返工次数后，Producer 应触发人工确认，而不是无限循环。
