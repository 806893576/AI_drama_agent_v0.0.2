# 安全合规分级设计

## 分级原因

短剧生产不同阶段的风险对象不同。输入请求、剧本文本、镜头描述、视觉 Prompt 和版权/IP 风险不能用同一套审核提示词处理。

## 审核层级

### 输入安全

文件：`safety/input_guard.py`

检查用户请求是否包含违法、高风险、侵权、真人仿冒、未成年人或明显不可继续的内容。

### 剧本安全

文件：`safety/script_guard.py`

检查故事设定、人物关系、台词、情节、敏感题材、平台审核风险和版权近似表达。

### 镜头与视听安全

文件：`safety/shot_guard.py`

检查分镜、表演、摄影、灯光、声音、特效中的高风险表达，尤其是镜头级可视化风险。

### 视觉 Prompt 安全

文件：`safety/prompt_guard.py`

检查图片/视频生成 Prompt 是否包含敏感视觉元素、不当人物设定、过度仿冒或平台不允许的生成要求。

### 版权/IP 风险

文件：`safety/copyright_guard.py`

检查是否明显模仿具体影视作品、明星、角色、商标或受保护视觉风格。

## 输出字段

安全审核应输出结构化结果：

```json
{
  "passed": true,
  "risk_level": "low",
  "risk_types": [],
  "evidence": [],
  "affected_artifacts": [],
  "repair_target": null,
  "suggested_changes": []
}
```
