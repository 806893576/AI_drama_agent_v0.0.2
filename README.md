# AI 短剧制作方案生成智能体

这是一个基于 Python、FastAPI 和 LangGraph 的 AI 短剧前期制作系统。用户只需要输入题材、故事构想、集数、单集时长和风格要求，系统就可以依次生成创意简报、风格指南、故事圣经、人物圣经、分集大纲、剧本、导演分镜、视听增强方案、美术资产 Prompt、审核报告和最终交付包。

当前版本：`v0.0.2`

> 本项目目前生成的是短剧制作方案、结构化 JSON 和图像/视频生成 Prompt，不会直接生成最终图片、音频或视频。`final_package` 可以继续交给图像生成、视频生成或其他制作工具使用。

## 目录

- [主要功能](#主要功能)
- [完整工作流程](#完整工作流程)
- [运行前准备](#运行前准备)
- [Windows 一键启动](#windows-一键启动)
- [手动安装和启动](#手动安装和启动)
- [配置真实大模型](#配置真实大模型)
- [第一次生成短剧](#第一次生成短剧)
- [网页页面完整操作指南](#网页页面完整操作指南)
- [人工确认和修改](#人工确认和修改)
- [单独运行导演视听或美术模块](#单独运行导演视听或美术模块)
- [内置风格预设](#内置风格预设)
- [生成文件位置](#生成文件位置)
- [生成文件内容说明](#生成文件内容说明)
- [最终交付包格式](#最终交付包格式)
- [命令行和 API 使用](#命令行和-api-使用)
- [常见问题](#常见问题)
- [安全和隐私](#安全和隐私)
- [开发与测试](#开发与测试)

## 主要功能

- 从自然语言需求生成完整短剧前期制作方案。
- 使用 LangGraph 管理编剧、导演、视听、美术、审核和返工流程。
- 支持本地美术风格和导演风格预设匹配、组合与统一约束。
- 支持完整模式、快速草案模式和自定义审核节点开关。
- 支持在创意简报、风格指南、分集大纲之后人工确认。
- 人工确认支持“语言修改”和“直接编辑 JSON”两种方式。
- 支持任务检查点、失败重试和断点继续，避免重复调用已完成节点。
- 支持只运行导演、视听或美术模块，方便局部测试和返工。
- 所有主要产物均保存为带版本号的 JSON 文件。
- 最终自动生成面向图像和视频生产的精简 `final_package`。
- 支持查看每次发送给真实 LLM 的完整 Prompt Trace。

## 完整工作流程

```text
用户需求
  -> 输入安全检查
  -> 创意简报 CreativeBrief
  -> 创意简报完整性校验
  -> [可选] 人工确认创意简报
  -> CreativeStyleGuide 风格指南
  -> [可选] 人工确认风格
  -> Story Bible 故事圣经
  -> Story Synopsis 故事梗概
  -> Character Bible 人物圣经
  -> Episode Outline 分集大纲
  -> [可选] 人工确认分集大纲
  -> Episode Script 分集剧本
  -> 对白润色
  -> 剧本审核 / 质量评分 / 安全审核 / 文本一致性审核
  -> 场景拆解
  -> 分镜设计
  -> 表演调度
  -> 视听增强
  -> 镜头安全审核
  -> 美术资产 Prompt
  -> Prompt 安全审核
  -> 资产注册
  -> 制作一致性审核
  -> 最终安全审核 / 最终验收
  -> final_package_v001.json
```

关闭某个审核开关后，对应审核节点不会执行，也不会产生该审核文件。创作主链路仍会继续。

## 运行前准备

### 必需软件

| 软件 | 要求 | 说明 |
| --- | --- | --- |
| Python | `3.11` 或更高版本 | 建议安装 64 位版本 |
| Git | 任意近期版本 | 用于从 GitHub 下载和更新项目 |
| 浏览器 | Chrome、Edge 等 | 用于打开本地操作页面 |
| 网络 | 安装依赖时需要 | 使用真实 LLM 时也需要 |

项目不需要 Node.js，不需要独立数据库，也不要求本机有 GPU。所有任务和生成结果默认保存在本地 JSON 文件中。

### 下载项目

打开 PowerShell 或 Windows Terminal，执行：

```powershell
git clone https://github.com/806893576/AI_drama_agent_v0.0.2.git
cd AI_agent_drama
```

如果是从 GitHub 网页下载 ZIP，请先解压，再进入包含 `app.py`、`run.bat` 和 `requirements.txt` 的目录。

## Windows 一键启动

这是最适合第一次使用者的方式。

### 第一步：创建配置文件

在项目根目录复制 `.env.example`，并把副本命名为 `.env`：

```powershell
Copy-Item .env.example .env
```

第一次只想确认程序能运行时，保持下面的配置即可：

```env
LLM_CLIENT=fake
```

`fake` 模式不会访问外部模型，也不会产生 API 费用。它主要用于检查流程、页面和文件结构，生成内容的创作质量不能代表真实模型效果。

### 第二步：运行启动脚本

双击项目根目录中的 `run.bat`。脚本会：

1. 创建本地 Python 虚拟环境 `.venv`。
2. 安装或检查运行依赖。
3. 启动本地服务。
4. 在命令窗口中显示页面地址。

看到下面的提示后，不要关闭命令窗口：

```text
Open test page: http://127.0.0.1:8000/
```

在浏览器打开：

- 操作页面：<http://127.0.0.1:8000/>
- API 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/v1/health>

停止服务时，回到命令窗口按 `Ctrl+C`。

## 手动安装和启动

如果一键脚本失败，或者希望完整安装所有开发依赖，请使用下面的方法。

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe app.py --serve --host 127.0.0.1 --port 8000
```

这里直接使用 `.venv` 中的 Python，不要求执行激活脚本，因此不会受到 PowerShell 执行策略影响。

### macOS / Linux

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
./.venv/bin/python app.py --serve --host 127.0.0.1 --port 8000
```

### 验证服务

浏览器访问 <http://127.0.0.1:8000/api/v1/health>。正常情况下会看到类似内容：

```json
{
  "status": "ok",
  "service": "Drama Agent Platform",
  "version": "0.0.3"
}
```

## 配置真实大模型

第一次建议先用 `fake` 模式完成一次短任务，确认安装、页面和文件保存都正常，再切换真实模型。

> `.env` 中包含 API Key，不能发给别人，也不要提交到 GitHub。项目已经通过 `.gitignore` 忽略 `.env`。

### DeepSeek

编辑 `.env`：

```env
LLM_CLIENT=deepseek
DEEPSEEK_API_KEY=替换成你的真实APIKey
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_STRUCTURED_MODEL=deepseek-chat
DEEPSEEK_REASON_MODEL=deepseek-reasoner
LLM_FORCE_JSON_OBJECT=false
LLM_TRACE_ENABLED=true
```

### OpenAI 或 OpenAI-compatible 服务

```env
LLM_CLIENT=openai
OPENAI_API_KEY=替换成你的真实APIKey
OPENAI_BASE_URL=https://api.openai.com
OPENAI_MODEL=gpt-4.1-mini
LLM_FORCE_JSON_OBJECT=false
LLM_TRACE_ENABLED=true
```

对于其他兼容 Chat Completions API 的服务，需要把 `OPENAI_BASE_URL`、`OPENAI_MODEL` 和 `OPENAI_API_KEY` 换成供应商提供的值。

### 常用环境变量

| 变量 | 默认值 | 作用 |
| --- | --- | --- |
| `LLM_CLIENT` | `fake` | 可选 `fake`、`deepseek`、`openai` |
| `OPENAI_API_KEY` | 空 | OpenAI-compatible API Key |
| `OPENAI_BASE_URL` | `https://api.openai.com` | OpenAI-compatible 服务地址 |
| `OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI-compatible 模型名称 |
| `DEEPSEEK_API_KEY` | 空 | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek 服务地址 |
| `DEEPSEEK_STRUCTURED_MODEL` | `deepseek-chat` | 结构化 JSON 生成模型 |
| `DEEPSEEK_REASON_MODEL` | `deepseek-reasoner` | 推理模型备用配置 |
| `LLM_FORCE_JSON_OBJECT` | `false` | 是否强制 JSON Object；当前部分 Prompt 输出数组，建议保持 `false` |
| `LLM_TRACE_ENABLED` | `true` | 是否保存并在网页显示完整 Prompt Trace |
| `LLM_MAX_RETRIES` | `2` | 网络或服务临时错误的自动重试次数 |
| `LLM_RETRY_BASE_DELAY` | `0.5` | 自动重试基础等待秒数 |
| `DRAMA_STORAGE_DIR` | `storage` | 所有运行数据的根目录 |

修改 `.env` 后需要停止并重新启动服务，新的配置才会生效。

## 第一次生成短剧

为了控制等待时间和真实模型费用，第一次建议生成一集、每集两分钟，并选择快速草案模式。

推荐输入模板：

```text
题材：都市悬疑短剧。
平台：抖音。
集数：1集。
单集时长：2分钟。
故事种子：女主在搬离公司当天发现一份可以证明合伙人侵占股份的录音。
整体基调：紧张、克制、结尾有反转。
美术风格：日式青春与赛璐璐动画融合。
导演风格：精密悬疑惊悚，强调视线、遮挡和声音线索。
```

操作顺序：

1. 打开 <http://127.0.0.1:8000/>。
2. 把需求粘贴到“输入需求”。
3. 第一次运行时让“任务 ID”保持为空。
4. 点击“快速草案模式”。
5. 暂时关闭“人工确认节点”，体验全自动流程。
6. 点击“执行当前配置”。
7. 等待右侧状态变为完成，并记录页面自动生成的 `job_id`。
8. 打开 `storage/artifacts/{job_id}/final_package/final_package_v001.json` 查看最终结果。

真实模型会按节点多次调用 API。集数越多、审核节点越多，等待时间和 token 消耗越高。

## 网页页面完整操作指南

### 顶部链接

| 控件 | 作用 |
| --- | --- |
| `API 文档` | 打开 FastAPI 自动生成的 Swagger 页面，可直接查看和调用接口 |
| `健康检查` | 检查服务是否正常启动，并显示当前版本 |

### 输入需求

页面左上方的大文本框是整个项目的创作入口。建议明确写出：

- 题材、平台和目标观众。
- 集数和单集时长。
- 主角、目标、阻力和故事种子。
- 美术风格、导演风格、摄影或声音倾向。
- 必须保持的规则和禁止出现的内容。

输入越明确，后续各节点越容易保持一致。不要在这里粘贴 API Key。

### 任务 ID 输入框

| 填法 | 效果 |
| --- | --- |
| 留空 | 浏览器自动创建形如 `job_12ab34cd56ef` 的新任务 ID |
| 填已有 ID | 如果找到检查点，默认从最后一个成功节点继续 |
| 填不存在的 ID | 使用这个 ID 创建新任务 |

任务 ID 同时也是本地输出目录名。建议不要手动使用斜杠、空格或特殊符号。

### 节点执行开关

绿色表示开启，灰色表示关闭。关闭后，该节点不会执行，也不会生成对应审核文件。

| 开关 | 作用 | 关闭后的影响 |
| --- | --- | --- |
| 剧本审核 | 检查剧情逻辑、人物动机、节奏、爽点、反转和平台适配 | 不生成 `script_review` |
| 质量评分 | 把审核结果量化，辅助返工路由 | 不生成 `quality_score` |
| 剧本文本安全审核 | 检查设定、剧情和台词的安全风险 | 不生成对应 `safety_review` |
| 文本一致性审核 | 检查人物关系、时间线、场景、道具和分集连续性 | 不生成文本一致性报告 |
| 镜头/视听安全审核 | 检查分镜、摄影、灯光、声音和特效风险 | 不生成镜头视听安全报告 |
| 视觉 Prompt 安全审核 | 检查图像 Prompt 的版权、肖像、品牌和平台风险 | 不生成 Prompt 安全报告 |
| 制作一致性审核 | 检查剧本、分镜、服装、道具、声音和资产引用 | 不生成制作一致性报告 |
| 最终安全审核 | 对最终汇总结果做最后一层安全检查 | 不生成最终安全报告 |
| 最终验收 | 检查关键交付物是否齐全 | 跳过制片人最终验收，但仍可生成最终包 |
| 人工确认节点 | 在创意简报、风格指南、分集大纲后暂停 | 关闭时全流程自动向下运行 |

“人工确认节点”是独立开关，不会被“恢复完整链路”或“快速草案模式”自动改变。

### 主操作按钮

| 按钮 | 具体作用 | 使用时机 |
| --- | --- | --- |
| `执行当前配置` | 使用当前需求、任务 ID 和开关运行任务；已有 ID 且有检查点时会继续 | 新建任务或按当前配置提交 |
| `继续已有任务` | 从已有任务最后成功的 checkpoint 恢复，不重复调用已完成节点 | LLM 网络失败、程序中断或人工暂停后继续 |
| `强制重跑` | 不读取旧 checkpoint，从输入端重新执行同一个任务 ID | 希望整条链重新生成时使用 |
| `恢复完整链路` | 把九个审核开关全部打开，只改变开关，不会立即运行 | 从快速模式切回完整模式 |
| `快速草案模式` | 把九个审核开关全部关闭，只保留创作和最终输出主链 | 首次测试、节省 token、快速查看草案 |

“强制重跑”不会删除旧产物。同一任务下再次保存同类产物时，文件版本通常会从 `v001` 增加到 `v002`。

### 运行状态显示栏

页面右侧会每秒刷新一次运行状态。

| 显示项 | 含义 |
| --- | --- |
| 状态 | 当前任务整体状态，例如 `running`、`completed`、`paused_or_rejected` 或 `failed` |
| 当前节点 | 正在执行或最近记录的 LangGraph 节点 |
| 阶段 | 当前处于简报、编剧、导演、视听、美术、审核或最终输出等阶段 |
| 最后完成 | 最近成功完成的节点，断点恢复会从它之后继续 |
| 已完成节点数 | 当前 checkpoint 已记录的成功节点数量 |
| 产物数 | 当前任务已经登记的 artifact 数量 |
| 状态说明 | 当前执行、暂停、失败或完成原因 |

人工确认导致的 `paused_or_rejected` 通常只是“等待用户确认”，不代表任务失败。

### 返回结果栏

深色的“返回结果”区域显示 API 返回的 JSON。常见字段：

| 字段 | 含义 |
| --- | --- |
| `job_id` | 本次任务 ID，也是输出目录名 |
| `status` | `completed` 或 `paused_or_rejected` |
| `final_output_ready` | 是否已经生成最终交付包 |
| `final_message` | 当前结果说明 |
| `human_confirmation_required` | 是否等待人工操作 |
| `human_confirmation_point` | 当前确认点：`brief`、`style` 或 `episode_outline` |
| `artifact_ids` | 已生成产物名称与版本 ID |
| `completed_nodes` | 已成功完成的节点列表 |
| `llm_format_error` | LLM JSON 格式或 Schema 校验错误 |
| `llm_runtime_error` | 网络、超时、SSL 或模型服务错误 |

### LLM Prompt Trace

启用 `LLM_TRACE_ENABLED=true` 并使用真实模型时，这里会显示每次请求的 Prompt。

| 控件 | 作用 |
| --- | --- |
| `刷新` | 重新读取当前任务的 Prompt Trace 列表 |
| Prompt 按钮 | 按 Prompt ID 打开某次调用 |
| 路径显示 | 显示该 Trace 在本地的保存位置 |
| Prompt 预览 | 显示完整 system/user 消息，便于调试 token 和上下文 |

`fake` 模式或关闭 Trace 时，这里可能没有内容。Prompt Trace 可能包含用户故事和完整创作上下文，分享前请检查隐私。

### LLM 格式错误面板

当真实模型返回的内容不是合法 JSON，或不符合目标 Schema 时，会出现：

| 按钮 | 作用 |
| --- | --- |
| `确认 LLM 修复并重新运行` | 从检查点继续，并把原始输出、错误和目标 Schema 交给 LLM 修复 |
| `退出本次任务` | 停止处理，不继续消耗 token |

### LLM 请求失败面板

网络、SSL、超时、限流或模型服务异常时会出现：

| 按钮 | 作用 |
| --- | --- |
| `从失败节点重试` | 使用同一任务 ID 从最后成功 checkpoint 继续 |
| `退出本次任务` | 停止本次操作，保留已完成产物和检查点 |

## 人工确认和修改

开启“人工确认节点”后，系统会依次在三个位置暂停：

1. `创意简报确认`：确认题材、平台、受众、集数、时长、故事种子和约束。
2. `创作风格确认`：确认美术、导演、摄影、灯光、色彩、表演、剪辑、声音和特效规则。
3. `分集大纲确认`：确认每一集的开场、冲突、事件、转折、高潮和结尾悬念。

### 人工确认面板按钮

| 按钮 | 作用 |
| --- | --- |
| `用语言修改` | 显示普通模式输入框，用自然语言提出修改意见 |
| `直接编辑 JSON` | 显示专家模式编辑框，并加载当前产物完整 JSON |
| `确认通过，继续生成` | 接受当前版本，自动继续到下一个阶段或下一个确认点 |
| `提交语言修改` | 调用 LLM 按修改意见生成新的结构化版本，保存后仍停留在确认点 |
| `校验并保存 JSON` | 不让 LLM 重写内容，直接校验并保存编辑后的 JSON |

### 普通模式

适合不会编辑 JSON 的用户。修改意见应明确指出修改范围和不可改变的内容：

```text
只修改第3集：结尾提前暴露闺蜜背叛，但不要改变女主夺回公司的长期目标，
不要修改第1、2、4集，也不要新增角色。
```

分集大纲修改只会向 LLM 提供目标集、相邻集和必要的自然语言摘要，不会反复发送全部人物圣经和故事 JSON。普通模式会产生额外 LLM token 消耗。

### 专家模式

适合熟悉 JSON 的用户。可以直接编辑当前产物，但必须：

- 保留原有字段名称和必填字段。
- 使用英文半角双引号 `"`。
- 不添加 JSON 注释。
- 保持 ID 唯一。
- 分集大纲中不能出现重复 `episode_number`。

提交后系统会执行 Pydantic Schema 校验。格式不合法时不会覆盖当前有效版本。

### 推荐确认流程

```text
查看当前内容
  -> 需要修改：选择普通模式或专家模式并提交
  -> 再次检查新版本
  -> 满意后点击“确认通过，继续生成”
```

人工修改会保存为新版本，并记录父产物 ID。修改早期产物后，系统会清理需要重新生成的下游状态，避免继续使用旧剧情或旧风格。

## 单独运行导演视听或美术模块

这一部分用于调试或局部返工。第一次使用项目时可以先忽略。

所有模块按钮都会创建新的输出任务 ID，不会覆盖源任务。输入框中的 artifact ID 留空时，会自动读取对应源任务的最新版本。

### 公共源任务

页面上方“任务 ID”是模块运行的默认源任务。模块必须先找到所需的上游文件。

### 模块输入框

| 输入框 | 哪个模块使用 | 作用 |
| --- | --- | --- |
| `episode_script artifact id` | 导演 | 指定剧本版本，例如 `episode_script_v002`；留空取最新版本 |
| `performance_direction artifact id` | 视听 | 指定表演调度版本；留空取最新版本 |
| `scene_breakdown 来源 job id` | 美术 | 场景拆解来自哪个任务；留空使用页面上方源任务 |
| `scene_breakdown artifact id` | 美术 | 指定场景拆解版本；留空取对应任务最新版本 |
| `audiovisual_enhanced_shot_list 来源 job id` | 美术 | 视听增强分镜来自哪个任务；留空使用页面上方源任务 |
| `audiovisual_enhanced_shot_list artifact id` | 美术 | 指定视听增强分镜版本；留空取最新版本 |
| `character_bible 来源 job id` | 美术，可选 | 从其他任务读取人物圣经 |
| `character_bible artifact id` | 美术，可选 | 指定人物圣经版本；两个角色输入框都留空时不加载人物圣经 |

### 模块按钮

| 按钮 | 必需上游产物 | 输出 |
| --- | --- | --- |
| `只运行导演模块` | `episode_script` | 场景拆解、分镜、表演调度、导演包 |
| `只运行视听模块` | `performance_direction` | 视听增强分镜和视听包 |
| `只运行美术组 Agent` | `scene_breakdown`、`audiovisual_enhanced_shot_list` | `art_package`；人物圣经可选 |

模块单独运行不会自动生成完整 `final_package`，因为它只执行选中的子流程。

## 内置风格预设

系统会从用户需求和 CreativeBrief 中匹配 `styles/presets/` 下的预设，最多融合四个匹配结果。没有匹配时使用默认电影感短剧和纪实现实主义预设。

在“输入需求”里直接写中文名称或常见别名即可，例如：

```text
美术风格：日式青春 + 赛璐璐动画。
导演风格：霓虹疏离电影诗 + 精密悬疑惊悚。
```

### 美术风格

- 默认电影感短剧、赛璐璐动画、日式青春、毛毡定格、剪纸定格、像素风。
- 温暖家庭向三维动画、水墨国风、水彩绘本、黏土定格、低多边形三维。
- 复古港风霓虹、赛博霓虹、黑色漫画、波普漫画、装饰艺术奢华。
- 粗野主义都市、动态矢量图形、转描动画、浮世绘版画、蒸汽波合成器浪潮。

### 导演风格

- 纪实现实主义、日式青春观察、精密悬疑惊悚、80年代港片动势。
- 梦魇异化美学、霓虹疏离电影诗、高饱和超现实棚拍、音乐视频高能节奏。
- 经典黑色电影、法国新浪潮、德国表现主义、苏联蒙太奇。
- 伪纪录发现影像、桌面屏幕电影。

如果输入真实导演、摄影师、片厂、品牌或具体作品名称，系统会尽量转译为色彩、光影、构图、材质、节奏和声音等描述性规则，最终 Prompt 不应要求直接复制版权角色或在世创作者风格。

## 生成文件位置

所有运行文件默认位于 `storage/`：

```text
storage/
├─ artifacts/
│  └─ {job_id}/
│     ├─ creative_brief/
│     ├─ style_guide/
│     ├─ story_bible/
│     ├─ character_bible/
│     ├─ episode_outline/
│     ├─ episode_script/
│     ├─ scene_breakdown/
│     ├─ audiovisual_enhanced_shot_list/
│     ├─ art_package/
│     └─ final_package/
├─ assets/
│  └─ {job_id}/asset_registry.json
├─ checkpoints/
│  └─ {job_id}.json
├─ database/
│  ├─ jobs.json
│  └─ evaluations.json
└─ llm_traces/
   └─ {job_id}/prompts/
```

其中 `{job_id}` 要替换为页面返回的真实任务 ID，例如：

```text
storage/artifacts/job_12ab34cd56ef/final_package/final_package_v001.json
```

这些运行目录已被 `.gitignore` 忽略，正常情况下不会上传到 GitHub。

## 生成文件内容说明

### 通用 Artifact 外壳

`storage/artifacts/` 中每个 JSON 都使用相同外壳，真正的业务内容在 `content` 中：

```json
{
  "artifact_id": "story_bible_v001",
  "job_id": "job_xxx",
  "artifact_type": "story_bible",
  "version": 1,
  "content": {},
  "summary": "产物摘要",
  "created_by": "writer.story_bible",
  "parent_artifact_id": null,
  "metadata": {},
  "created_at": "2026-10-23T00:00:00Z"
}
```

| 外壳字段 | 含义 |
| --- | --- |
| `artifact_id` | 产物 ID，通常包含版本号 |
| `job_id` | 所属任务 |
| `artifact_type` | 产物类型，也是目录名 |
| `version` | 当前版本数字 |
| `content` | 真正需要阅读或交给下游使用的内容 |
| `summary` | 人类可读摘要 |
| `created_by` | 生成该产物的节点 |
| `parent_artifact_id` | 上一个版本或上游产物，用于追踪来源 |
| `metadata` | 扩展元数据 |
| `created_at` | UTC 创建时间 |

### 需求与风格阶段

| 路径 | 主要内容 |
| --- | --- |
| `creative_brief/creative_brief_v001.json` | 题材、平台、受众、集数、时长、基调、风格关键词、故事种子、限制和禁止元素 |
| `brief_validation/brief_validation_v001.json` | 简报是否完整、缺失字段、系统假设和需要用户回答的问题 |
| `style_guide/style_guide_v001.json` | 美术、导演、摄影、灯光、色彩、服化道、渲染、表演、剪辑、声音、特效和安全规则 |

### 编剧阶段

| 路径 | 主要内容 |
| --- | --- |
| `story_bible/story_bible_v001.json` | 剧名、故事总结、主题、世界规则、核心冲突、时间线规则和不可变事实 |
| `story_synopsis/story_synopsis_v001.json` | 故事前提、主角目标、完整主线、转折、冲突、因果链、人物弧光、高潮和结局 |
| `character_bible/character_bible_v001.json` | 人物卡、人物关系和人物分组 |
| `episode_outline/episode_outline_v001.json` | 每集定位、开场钩子、核心冲突、关键事件、关系变化、情绪节点、高潮和悬念 |
| `episode_script/episode_script_v001.json` | 分集剧本数组，包括剧集元数据、场景、动作和对白 |
| `dialogue_polish/dialogue_polish_v001.json` | 对白、角色声口和节奏润色记录 |
| `writer_package/writer_package_v001.json` | 编剧阶段产物 ID、故事摘要、人物 ID 和剧集 ID 汇总 |

### 审核和返工阶段

| 路径 | 主要内容 |
| --- | --- |
| `script_review/script_review_v001.json` | 是否通过、整体评价、问题、优点和修改建议 |
| `quality_score/quality_score_v001.json` | 总分、分项分数、最弱维度、阈值和总结 |
| `safety_review/safety_review_{层级}_v001.json` | 风险等级、风险类型、问题、受影响产物和安全改写建议 |
| `continuity_review/continuity_review_{类型}_v001.json` | 文本或制作一致性结果，以及检查过的角色、场景、道具和镜头 ID |
| `repair_plan/repair_plan_v001.json` | 出现问题时的局部返工目标、范围、保留内容、指令和重试次数 |

关闭对应审核开关时，这些文件不会生成。没有触发返工时通常也不会出现 `repair_plan`。

### 导演与视听阶段

| 路径 | 主要内容 |
| --- | --- |
| `scene_breakdown/scene_breakdown_v001.json` | 场景 ID、集数、内外景、时间、地点、人物、道具、服化、动作、戏剧功能和连续性 |
| `shot_list/shot_list_v001.json` | 分镜 ID、场景 ID、镜号、景别、构图、镜头内容、机位运动、时长和连续性 |
| `performance_direction/performance_direction_v001.json` | 在分镜结构上加入人物站位、动作、表情和表演调度 |
| `director_package/director_package_v001.json` | 导演阶段产物引用、场景 ID、分镜 ID 和表演分镜 ID |
| `audiovisual_enhanced_shot_list/audiovisual_enhanced_shot_list_v001.json` | 加入摄影、光影、声音和必要特效后的最终分镜数组 |
| `audiovisual_package/audiovisual_package_v001.json` | 视听增强分镜引用、源镜头和增强镜头索引、数量与不改剧情原则 |

### 美术和资产阶段

| 路径 | 主要内容 |
| --- | --- |
| `art_package/art_package_v001.json` | 总体画风、角色/场景/道具生成 Prompt，以及每个分镜引用哪些资产 |
| `asset_registry/asset_registry_v001.json` | 角色、场景、道具、镜头和 Prompt 的统一资产登记表 |
| `storage/assets/{job_id}/asset_registry.json` | 不带 Artifact 外壳的原始资产注册表副本 |

`art_package` 中的 Prompt 是供外部图片生成工具使用的文字，不是已经生成好的图片。

### 系统运行文件

| 路径 | 作用 |
| --- | --- |
| `storage/checkpoints/{job_id}.json` | 最近成功节点后的完整恢复状态 |
| `storage/database/jobs.json` | 所有任务的状态、最终消息、产物 ID 和事件数 |
| `storage/database/evaluations.json` | 质量评估记录 |
| `storage/llm_traces/{job_id}/prompts/` | 完整 Prompt、模型响应、错误和 token usage 等调试信息 |

## 最终交付包格式

最终文件：

```text
storage/artifacts/{job_id}/final_package/final_package_v001.json
```

它的 `content` 同时保留产物索引、验收结果和供下游图像/视频生成使用的精简数据：

```json
{
  "package_id": "final_package_v001",
  "schema_version": "1.0",
  "job_id": "job_xxx",
  "source_artifact_ids": {
    "art_package": "art_package_v001",
    "audiovisual_enhanced_shot_list": "audiovisual_enhanced_shot_list_v001"
  },
  "art_package": {
    "style_profile": "统一美术风格描述",
    "character_assets": [
      {
        "character_name": "林知夏",
        "variant": "base",
        "prompt": "角色图生成提示词"
      }
    ],
    "scene_assets": [
      {
        "scene": ["EP_001_SC_001_公司前台"],
        "prompt": "场景图生成提示词"
      }
    ],
    "prop_assets": [
      {
        "prop_name": "银色行李箱",
        "used_in_scene_ids": ["EP_001_SC_001"],
        "prompt": "道具图生成提示词"
      }
    ]
  },
  "audiovisual_enhanced_shot_list": [
    {
      "shot_id": "EP_001_SC_001_shot_01",
      "scene": ["EP_001_SC_001_公司前台"],
      "shot_number": 1,
      "characters": ["林知夏_base"],
      "props": ["银色行李箱"],
      "shot_content": "视频生成提示词",
      "continuity": "与前后镜头的连续性说明"
    }
  ],
  "summary": "最终结果摘要",
  "artifact_refs": {},
  "acceptance": {},
  "sections": {}
}
```

其中：

- `scene` 固定使用 `["scene_id_scene_name"]`。
- `characters` 固定使用 `["character_name_variant"]`。
- `props` 直接使用道具名称列表。
- 场景、角色和道具由本地程序通过 `shot_id` 和 `art_package.shot_prompt_plan` 关联，不会再次调用 LLM。
- `shot_content` 来自视听增强后的最终分镜，可作为视频生成器的主要提示词。
- `continuity` 用于约束人物站位、动作、道具、光影、声音和前后镜头衔接。

## 命令行和 API 使用

### 命令行直接生成

```powershell
.\.venv\Scripts\python.exe app.py --request "都市悬疑短剧，1集，每集2分钟。"
```

快速草案：

```powershell
.\.venv\Scripts\python.exe app.py --request "都市悬疑短剧，1集，每集2分钟。" --fast-draft
```

命令行默认任务 ID 是 `job_debug`。频繁使用时建议通过网页或 API 指定独立任务 ID。

### API

启动服务后打开 <http://127.0.0.1:8000/docs>，可以直接在网页中测试所有接口。

创建任务的核心接口：

```text
POST /api/v1/jobs
```

示例请求：

```json
{
  "job_id": "job_demo_001",
  "user_request": "都市悬疑短剧，1集，每集2分钟，赛璐璐动画风格。",
  "execution_options": {
    "run_script_review": true,
    "run_quality_scoring": true,
    "run_script_safety": true,
    "run_text_continuity": true,
    "run_shot_av_safety": true,
    "run_prompt_safety": true,
    "run_production_continuity": true,
    "run_final_safety": true,
    "run_final_acceptance": true,
    "enable_human_confirmations": false
  },
  "llm_format_mode": "interrupt",
  "resume_from_checkpoint": false,
  "force_restart": false
}
```

常用只读接口：

| 接口 | 作用 |
| --- | --- |
| `GET /api/v1/health` | 健康检查 |
| `GET /api/v1/jobs/{job_id}` | 查询已保存任务摘要 |
| `GET /api/v1/jobs/{job_id}/runtime-status` | 查询实时节点和产物状态 |
| `GET /api/v1/jobs/{job_id}/llm-prompts` | 查询 Prompt Trace 列表 |
| `GET /api/v1/jobs/{job_id}/artifacts/{artifact_key}` | 读取人工确认所需产物内容 |

## 常见问题

### 双击 `run.bat` 后提示找不到 Python

安装 Python 3.11 或更高版本。Windows 安装时勾选 `Add Python to PATH`，安装完成后重新打开命令窗口。

检查命令：

```powershell
py --version
python --version
```

### PowerShell 不允许激活虚拟环境

无需修改系统执行策略，直接使用：

```powershell
.\.venv\Scripts\python.exe app.py --serve
```

### 依赖安装失败

先升级 pip，再重试：

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果仍失败，请检查代理、网络和 Python 版本。

### 端口 8000 已被占用

改用其他端口：

```powershell
.\.venv\Scripts\python.exe app.py --serve --port 8001
```

然后访问 <http://127.0.0.1:8001/>。

### 页面可以打开，但真实模型没有被调用

检查 `.env`：

- `LLM_CLIENT` 是否仍然是 `fake`。
- API Key 是否为空。
- 修改 `.env` 后是否重启了服务。
- Key 是否与所选供应商匹配。

### 真实模型调用费用过高

- 第一次只生成一集、两分钟。
- 使用“快速草案模式”。
- 关闭暂时不需要的审核节点。
- 人工确认普通模式只描述目标集，不要要求重写全部内容。
- 在 Prompt Trace 中检查是否有不必要的大段上下文。

### 状态显示 `paused_or_rejected`

先看右侧提示：

- 显示创意简报、风格或大纲确认：这是正常人工暂停。
- 显示 `llm_format_error`：模型输出 JSON 格式失败，可确认修复。
- 显示 `llm_runtime_error`：网络或模型服务失败，可从失败节点重试。
- 显示审核不通过：查看对应 review 和 repair plan 文件。

### 找不到生成文件

先从返回结果复制 `job_id`，再打开：

```text
storage/artifacts/{job_id}/
```

如果设置了 `DRAMA_STORAGE_DIR`、`DRAMA_ARTIFACT_DIR` 等变量，文件会保存在自定义目录。

### 为什么同一目录有 `v001`、`v002`

系统不会直接覆盖旧版本。人工修改、返工或强制重跑会生成新版本，方便比较和回退。通常编号最大的文件是最新版本。

### Prompt Trace 没有内容

可能原因：

- 当前使用 `fake` 模式。
- `.env` 中 `LLM_TRACE_ENABLED=false`。
- 当前节点使用本地确定性组装，没有调用 LLM。
- 页面上的任务 ID 不是需要查询的任务。

### 单独运行模块提示找不到 Artifact

确认：

- 页面上方任务 ID 是正确的源任务。
- 源任务已经生成该模块所需的上游文件。
- 手动填写的 artifact ID 包含完整版本号。
- 如果不确定版本，清空 artifact ID 输入框，让系统读取最新版本。

## 安全和隐私

- 不要提交 `.env`、API Key、个人隐私数据或未授权素材。
- `storage/` 下可能包含完整剧情、Prompt、模型原始输出和错误信息，分享前应检查。
- `.gitignore` 默认排除了 `.env`、运行产物、检查点、数据库、Trace、日志、缓存和虚拟环境。
- 上传 GitHub 前建议执行 `git status`，确认没有密钥或私人素材被加入。
- 使用真实品牌、明星、版权角色或具体创作者参考时，应遵守相关法律、平台规则和供应商政策。

## 开发与测试

运行完整测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

当前版本测试结果：

```text
107 passed
```

### 主要目录

```text
agents/                 Agent 角色实现
api/                    FastAPI 接口和本地网页
core/                   配置、常量和生命周期
database/               本地 JSON 数据库
domain/                 Pydantic 业务模型
graph/                  LangGraph 主图、节点、路由和子图
memory/                 checkpoint 存储
prompts/                所有 LLM Prompt 模板
services/               LLM、存储、风格和人工确认服务
state/                  Graph State、事件和产物引用
styles/presets/         美术与导演风格预设库
storage/                本地运行产物，默认不提交 Git
tests/                  单元测试、集成测试和评测
workflows/              完整任务与模块任务入口
```

更多技术文档：

- [真实 LLM 接入说明](docs/llm_integration.md)
- [执行选项说明](docs/execution_options.md)
- [生成文件详细格式](docs/保存格式.md)
- [关键节点输入输出](docs/关键节点输入输出.md)
