"""API 服务入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

from api.routes import router
from core.lifecycle import shutdown, startup
from core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        startup()
        yield
        shutdown()

    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    app.include_router(router)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> str:
        # 本地网页端入口：用于人工提交任务，并按需关闭高成本审核节点。
        return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Drama Agent Platform</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f6fa;
      --panel: #ffffff;
      --line: #d8deea;
      --text: #172033;
      --muted: #637083;
      --blue: #165dff;
      --green: #0f8f5f;
      --orange: #c46a12;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, "Microsoft YaHei", sans-serif;
    }
    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 28px;
    }
    header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 18px;
    }
    h1 { margin: 0; font-size: 26px; }
    h2 { margin: 0 0 12px; font-size: 18px; }
    p { margin: 8px 0 0; color: var(--muted); line-height: 1.6; }
    a { color: var(--blue); text-decoration: none; }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(360px, .95fr);
      gap: 16px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    textarea {
      width: 100%;
      min-height: 136px;
      resize: vertical;
      border: 1px solid #c8d0df;
      border-radius: 6px;
      padding: 12px;
      font-size: 14px;
      line-height: 1.6;
    }
    input[type="text"] {
      width: 100%;
      border: 1px solid #c8d0df;
      border-radius: 6px;
      padding: 10px 12px;
      font-size: 14px;
    }
    .row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 0;
      border-bottom: 1px solid #edf1f7;
    }
    .row:last-child { border-bottom: 0; }
    .label strong { display: block; font-size: 14px; }
    .label span { display: block; color: var(--muted); font-size: 12px; margin-top: 3px; }
    .switch {
      position: relative;
      width: 44px;
      height: 24px;
      flex: 0 0 auto;
    }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute;
      cursor: pointer;
      inset: 0;
      background: #a8b2c1;
      transition: .18s;
      border-radius: 999px;
    }
    .slider:before {
      position: absolute;
      content: "";
      height: 18px;
      width: 18px;
      left: 3px;
      top: 3px;
      background: white;
      transition: .18s;
      border-radius: 50%;
      box-shadow: 0 1px 3px rgba(0,0,0,.2);
    }
    input:checked + .slider { background: var(--green); }
    input:checked + .slider:before { transform: translateX(20px); }
    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 14px;
    }
    button {
      border: 0;
      border-radius: 6px;
      padding: 10px 14px;
      color: white;
      background: var(--blue);
      cursor: pointer;
      font-size: 14px;
    }
    button.secondary { background: #45556c; }
    button.fast { background: var(--orange); }
    button:disabled { opacity: .62; cursor: wait; }
    pre {
      min-height: 360px;
      max-height: 640px;
      overflow: auto;
      margin: 0;
      padding: 14px;
      color: #e5e7eb;
      background: #0f172a;
      border-radius: 6px;
      line-height: 1.5;
      white-space: pre-wrap;
    }
    .hint {
      font-size: 12px;
      color: var(--muted);
      margin-top: 10px;
    }
    .notice {
      display: none;
      margin-top: 12px;
      padding: 12px;
      border: 1px solid #f0c36d;
      background: #fff8e6;
      border-radius: 6px;
    }
    .notice strong { display: block; margin-bottom: 6px; color: #8a5200; }
    .notice code {
      display: block;
      max-height: 180px;
      overflow: auto;
      white-space: pre-wrap;
      padding: 10px;
      background: #fff;
      border: 1px solid #ecd8a6;
      border-radius: 5px;
      color: #394150;
      font-size: 12px;
    }
    .repair-actions {
      display: flex;
      gap: 10px;
      margin-top: 10px;
      flex-wrap: wrap;
    }
    button.danger { background: #9f2d2d; }
    .prompt-tools {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-top: 16px;
    }
    .prompt-tools h2 { margin: 0; }
    .prompt-tools button {
      padding: 7px 10px;
      background: #45556c;
      font-size: 12px;
    }
    .prompt-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 8px 0;
    }
    .prompt-list button {
      max-width: 100%;
      padding: 7px 9px;
      background: #eef3ff;
      color: #18345f;
      border: 1px solid #cbd8f0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .prompt-path {
      display: none;
      overflow-wrap: anywhere;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    pre.prompt-preview {
      display: none;
      min-height: 180px;
      max-height: 480px;
      margin-top: 8px;
      background: #111827;
    }
    .runtime-panel {
      margin-bottom: 14px;
      padding: 12px;
      border: 1px solid #cbd8f0;
      background: #f8fbff;
      border-radius: 6px;
    }
    .runtime-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px 12px;
      margin-top: 8px;
      font-size: 13px;
    }
    .runtime-grid span { color: var(--muted); }
    .runtime-grid strong {
      display: block;
      margin-top: 3px;
      color: var(--text);
      word-break: break-word;
    }
    .status-running { color: var(--blue); }
    .status-failed { color: #9f2d2d; }
    @media (max-width: 880px) {
      main { padding: 16px; }
      header { display: block; }
      .layout { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>AI 短剧制作方案生成智能体</h1>
        <p>提交任务时可以关闭部分审核节点，用于快速草案、降低 token 消耗，或按阶段调试链路。</p>
      </div>
      <p><a href="/docs">API 文档</a> · <a href="/api/v1/health">健康检查</a></p>
    </header>

    <div class="layout">
      <section>
        <h2>输入需求</h2>
        <textarea id="request">美术风格：邵氏电影风格、复古港风。题材：古装武侠题材。平台：抖音。集数：1集。单集时长：2分钟。故事种子：武林大会最后一场决斗。年轻高手对阵白发老人。所有人都认为老人必败。开战后，老人只守不攻。年轻人连续出招，却始终无法伤他。年轻高手气急败坏，出言嘲讽。白发老人微微一笑，使出诡异的身法来到年轻高手身旁，一掌将其击倒。年轻高手心服口服的认输。</textarea>
        <h2 style="margin-top: 18px;">任务 ID</h2>
        <input id="jobId" type="text" placeholder="留空则创建新任务；填入已有 job_id 可断点继续" />
        <p class="hint">填入已有任务 ID 时，默认从最后成功 checkpoint 继续；需要重做时使用强制重跑。</p>

        <h2 style="margin-top: 18px;">节点执行开关</h2>
        <div id="options"></div>
        <p class="hint">开关关闭后，对应节点不会执行，也不会生成对应 artifact。默认全部开启。</p>
        <div class="row">
          <div class="label">
            <strong>人工确认节点</strong>
            <span>开启后会在创意简报、风格指南、分集大纲三个早期节点暂停，支持语言修改或直接编辑 JSON。</span>
          </div>
          <label class="switch" title="人工确认节点">
            <input type="checkbox" id="enableHumanConfirmations" />
            <span class="slider"></span>
          </label>
        </div>

        <div class="actions">
          <button id="submit">执行当前配置</button>
          <button id="resumeJob" class="secondary">继续已有任务</button>
          <button id="restartJob" class="danger">强制重跑</button>
          <button id="full" class="secondary">恢复完整链路</button>
          <button id="fast" class="fast">快速草案模式</button>
        </div>

        <h2 style="margin-top: 18px;">模块单独运行</h2>
        <p class="hint">使用上方任务 ID 作为源任务；artifact id 留空时读取该源任务最新版本。</p>
        <input id="moduleEpisodeScript" type="text" placeholder="episode_script artifact id，可留空" />
        <input id="modulePerformanceDirection" type="text" placeholder="performance_direction artifact id，可留空" />
        <input id="moduleSceneBreakdownJob" type="text" placeholder="scene_breakdown 来源 job id，可留空" />
        <input id="moduleSceneBreakdown" type="text" placeholder="scene_breakdown artifact id，可留空" />
        <input id="moduleAvEnhancedJob" type="text" placeholder="audiovisual_enhanced_shot_list 来源 job id，可留空" />
        <input id="moduleAvEnhanced" type="text" placeholder="audiovisual_enhanced_shot_list artifact id，可留空" />
        <input id="moduleCharacterBibleJob" type="text" placeholder="character_bible 来源 job id，可选" />
        <input id="moduleCharacterBible" type="text" placeholder="character_bible artifact id，可选" />
        <div class="actions">
          <button id="runDirectorModule" class="secondary" type="button">只运行导演模块</button>
          <button id="runAvModule" class="secondary" type="button">只运行视听模块</button>
          <button id="runArtModule" class="secondary" type="button">只运行美术组 Agent</button>
        </div>
      </section>

      <section>
        <h2>返回结果</h2>
        <div id="runtimePanel" class="runtime-panel">
          <h2>运行状态</h2>
          <div class="runtime-grid">
            <div><span>状态</span><strong id="runtimeStatus">等待提交</strong></div>
            <div><span>当前节点</span><strong id="runtimeNode">-</strong></div>
            <div><span>阶段</span><strong id="runtimeStage">-</strong></div>
            <div><span>最后完成</span><strong id="runtimeLastNode">-</strong></div>
            <div><span>已完成节点数</span><strong id="runtimeCompletedCount">0</strong></div>
            <div><span>产物数</span><strong id="runtimeArtifactCount">0</strong></div>
          </div>
          <p class="hint" id="runtimeMessage">运行中会自动刷新当前节点。</p>
        </div>
        <pre id="output">等待提交...</pre>
        <div id="repairPanel" class="notice"></div>
        <div class="prompt-tools">
          <h2>LLM Prompt Trace</h2>
          <button id="refreshPrompts" type="button">刷新</button>
        </div>
        <p class="hint" id="promptHint">任务运行后，这里会列出每次送入 LLM 前组装好的完整 prompt。</p>
        <div id="promptList" class="prompt-list"></div>
        <div id="promptPath" class="prompt-path"></div>
        <pre id="promptPreview" class="prompt-preview"></pre>
      </section>
    </div>
  </main>

  <script>
    const optionDefs = [
      ["run_script_review", "剧本审核", "检查剧情逻辑、人物动机、节奏、爽点、反转和平台适配。"],
      ["run_quality_scoring", "质量评分", "把审核结果量化为分数，用于稳定路由和返工判断。"],
      ["run_script_safety", "剧本文本安全审核", "检查文本、人物设定和台词的安全合规风险。"],
      ["run_text_continuity", "文本一致性审核", "检查人物关系、时间线、场景、道具和分集连续性。"],
      ["run_shot_av_safety", "镜头/视听安全审核", "检查分镜、表演、摄影、灯光、声音和特效描述。"],
      ["run_prompt_safety", "视觉 Prompt 安全审核", "检查图片 Prompt 的视觉安全、版权和平台风险。"],
      ["run_production_continuity", "制作一致性审核", "检查剧本、分镜、资产、道具、服装、声音引用关系。"],
      ["run_final_safety", "最终安全审核", "对汇总交付包做最后一层安全检查。"],
      ["run_final_acceptance", "最终验收", "制片人验收关键交付物是否齐全。"]
    ];

    const optionsEl = document.getElementById("options");
    const output = document.getElementById("output");
    const repairPanel = document.getElementById("repairPanel");
    const submit = document.getElementById("submit");
    const promptList = document.getElementById("promptList");
    const promptPath = document.getElementById("promptPath");
    const promptPreview = document.getElementById("promptPreview");
    const promptHint = document.getElementById("promptHint");
    const refreshPrompts = document.getElementById("refreshPrompts");
    const jobIdInput = document.getElementById("jobId");
    const runDirectorModule = document.getElementById("runDirectorModule");
    const runAvModule = document.getElementById("runAvModule");
    const runArtModule = document.getElementById("runArtModule");
    const runtimeStatus = document.getElementById("runtimeStatus");
    const runtimeNode = document.getElementById("runtimeNode");
    const runtimeStage = document.getElementById("runtimeStage");
    const runtimeLastNode = document.getElementById("runtimeLastNode");
    const runtimeCompletedCount = document.getElementById("runtimeCompletedCount");
    const runtimeArtifactCount = document.getElementById("runtimeArtifactCount");
    const runtimeMessage = document.getElementById("runtimeMessage");
    let lastPayload = null;
    let lastJobId = null;
    let runtimePollTimer = null;
    let activeHumanConfirmation = null;
    let activeHumanArtifactKey = null;
    let activeHumanArtifactContent = null;

    function renderOptions() {
      optionsEl.innerHTML = optionDefs.map(([key, title, desc]) => `
        <div class="row">
          <div class="label">
            <strong>${title}</strong>
            <span>${desc}</span>
          </div>
          <label class="switch" title="${title}">
            <input type="checkbox" id="${key}" checked />
            <span class="slider"></span>
          </label>
        </div>
      `).join("");
    }

    function setAll(value) {
      optionDefs.forEach(([key]) => document.getElementById(key).checked = value);
    }

    function setFastDraft() {
      setAll(false);
    }

    function collectOptions() {
      const options = {};
      optionDefs.forEach(([key]) => {
        options[key] = document.getElementById(key).checked;
      });
      const skippedExecutionNode = Object.values(options).some(value => value === false);
      options.enable_human_confirmations = document.getElementById("enableHumanConfirmations").checked;
      if (skippedExecutionNode) {
        options.skipped_reason = "web_custom";
      }
      return options;
    }

    function clearRepairPanel() {
      repairPanel.style.display = "none";
      repairPanel.innerHTML = "";
    }

    function clearPromptPanel(message = "任务运行后，这里会列出每次送入 LLM 前组装好的完整 prompt。") {
      promptHint.textContent = message;
      promptList.innerHTML = "";
      promptPath.style.display = "none";
      promptPath.textContent = "";
      promptPreview.style.display = "none";
      promptPreview.textContent = "";
    }

    function renderRepairPanel(data) {
      const error = data.llm_format_error || {};
      repairPanel.style.display = "block";
      repairPanel.innerHTML = `
        <strong>LLM 结构化输出失败，需要你确认下一步</strong>
        <p>失败节点：${error.prompt_id || "未知"}</p>
        <p>错误信息：</p>
        <code>${escapeHtml(error.error_message || "")}</code>
        <p>模型原始输出预览：</p>
        <code>${escapeHtml(error.raw_output || "")}</code>
        <p>目标 Schema：</p>
        <code>${escapeHtml(JSON.stringify(error.target_schema || {}, null, 2))}</code>
        <div class="repair-actions">
          <button id="confirmRepair">确认 LLM 修复并重新运行</button>
          <button id="exitJob" class="danger">退出本次任务</button>
        </div>
      `;
      document.getElementById("confirmRepair").onclick = () => submitJob("auto_repair", lastJobId, true);
      document.getElementById("exitJob").onclick = () => {
        clearRepairPanel();
        output.textContent = "已退出。本次任务未继续提交 LLM 修复。\\n\\n" + output.textContent;
      };
    }

    function renderRuntimePanel(data) {
      const error = data.llm_runtime_error || {};
      repairPanel.style.display = "block";
      repairPanel.innerHTML = `
        <strong>LLM 请求失败，任务已暂停</strong>
        <p>失败节点：${error.prompt_id || "未知"}</p>
        <p>错误信息：</p>
        <code>${escapeHtml(error.error_message || "")}</code>
          <p>这类错误通常来自网络、SSL、超时或模型服务波动。系统没有把规则兜底内容写成正式创作产物。</p>
          <p>重试会从最后一个成功检查点继续，不会重复请求已完成的上游节点。</p>
        <div class="repair-actions">
          <button id="retryJob">从失败节点重试</button>
          <button id="exitJob" class="danger">退出本次任务</button>
        </div>
      `;
      document.getElementById("retryJob").onclick = () => submitJob("interrupt", lastJobId, true);
      document.getElementById("exitJob").onclick = () => {
        clearRepairPanel();
        output.textContent = "已退出。本次任务未继续提交 LLM。\\n\\n" + output.textContent;
      };
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function startRuntimePolling(jobId) {
      stopRuntimePolling();
      if (!jobId) {
        renderRuntimeStatus({ status: "unknown", message: "尚未确定任务 ID。" });
        return;
      }
      loadRuntimeStatus(jobId);
      runtimePollTimer = window.setInterval(() => loadRuntimeStatus(jobId), 1000);
    }

    function stopRuntimePolling() {
      if (runtimePollTimer) {
        window.clearInterval(runtimePollTimer);
        runtimePollTimer = null;
      }
    }

    async function loadRuntimeStatus(jobId = lastJobId) {
      if (!jobId) {
        return;
      }
      try {
        const response = await fetch(`/api/v1/jobs/${encodeURIComponent(jobId)}/runtime-status`);
        const data = await response.json();
        renderRuntimeStatus(data);
      } catch (error) {
        renderRuntimeStatus({ status: "unknown", message: String(error) });
      }
    }

    function renderRuntimeStatus(data) {
      const statusText = data.status || "unknown";
      runtimeStatus.textContent = statusText;
      runtimeStatus.className = statusText === "running"
        ? "status-running"
        : (statusText === "failed" ? "status-failed" : "");
      runtimeNode.textContent = data.current_node || "-";
      runtimeStage.textContent = data.current_stage || "-";
      runtimeLastNode.textContent = data.last_completed_node || "-";
      runtimeCompletedCount.textContent = String((data.completed_nodes || []).length);
      runtimeArtifactCount.textContent = String(Object.keys(data.artifact_ids || {}).length);
      runtimeMessage.textContent = data.message || "暂无运行状态。";
    }

    async function renderHumanConfirmationPanel(data) {
      activeHumanConfirmation = data;
      activeHumanArtifactKey = Object.keys(data.editable_artifact_refs || {})[0] || null;
      activeHumanArtifactContent = null;
      let artifactText = "{}";
      if (activeHumanArtifactKey) {
        try {
          const artifact = await loadEditableArtifact(activeHumanArtifactKey);
          activeHumanArtifactContent = artifact.content;
          artifactText = JSON.stringify(artifact.content, null, 2);
        } catch (error) {
          artifactText = JSON.stringify({ error: String(error) }, null, 2);
        }
      }
      repairPanel.style.display = "block";
      repairPanel.innerHTML = `
        <strong>人工确认节点：${escapeHtml(labelHumanPoint(data.human_confirmation_point))}</strong>
        <p>${escapeHtml(data.final_message || "请确认当前产物，或提交修改意见。")}</p>
        <ul>${(data.human_questions || []).map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        <div class="repair-actions">
          <button id="humanModeNormal" type="button">用语言修改</button>
          <button id="humanModeExpert" class="secondary" type="button">直接编辑 JSON</button>
          <button id="humanApprove" type="button">确认通过，继续生成</button>
        </div>
        <div id="humanNormalPanel">
          <p class="hint">普通模式：描述你想调整的剧情、风格或分集走向，系统会生成新的结构化版本。</p>
          <textarea id="humanFeedback" placeholder="例如：第3集结尾提前暴露闺蜜背叛，但不要改变女主目标。"></textarea>
          <div class="repair-actions">
            <button id="humanSubmitNormal" type="button">提交语言修改</button>
          </div>
        </div>
        <div id="humanExpertPanel" style="display:none;">
          <p class="hint">专家模式：直接编辑当前 artifact JSON。提交后会先做结构化校验。</p>
          <textarea id="humanArtifactJson">${escapeHtml(artifactText)}</textarea>
          <div class="repair-actions">
            <button id="humanSubmitExpert" type="button">校验并保存 JSON</button>
          </div>
        </div>
      `;
      document.getElementById("humanModeNormal").onclick = () => setHumanMode("normal");
      document.getElementById("humanModeExpert").onclick = () => setHumanMode("expert");
      document.getElementById("humanApprove").onclick = () => submitHumanConfirmation("approve", "normal");
      document.getElementById("humanSubmitNormal").onclick = () => submitHumanConfirmation("revise", "normal");
      document.getElementById("humanSubmitExpert").onclick = () => submitHumanConfirmation("revise", "expert");
    }

    function setHumanMode(mode) {
      document.getElementById("humanNormalPanel").style.display = mode === "normal" ? "block" : "none";
      document.getElementById("humanExpertPanel").style.display = mode === "expert" ? "block" : "none";
    }

    function labelHumanPoint(point) {
      return {
        brief: "创意简报确认",
        style: "创作风格确认",
        episode_outline: "分集大纲确认"
      }[point] || point || "人工确认";
    }

    async function loadEditableArtifact(artifactKey) {
      const response = await fetch(
        `/api/v1/jobs/${encodeURIComponent(lastJobId)}/artifacts/${encodeURIComponent(artifactKey)}`
      );
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return await response.json();
    }

    async function submitHumanConfirmation(action, mode) {
      if (!lastJobId || !activeHumanConfirmation) {
        output.textContent = "当前没有可提交的人工确认任务。";
        return;
      }
      let artifactContent = null;
      if (action === "revise" && mode === "expert") {
        try {
          artifactContent = JSON.parse(document.getElementById("humanArtifactJson").value);
        } catch (error) {
          output.textContent = `JSON 格式错误：${error}`;
          return;
        }
      }
      const payload = {
        confirmation_point: activeHumanConfirmation.human_confirmation_point,
        action,
        mode,
        feedback: action === "revise" && mode === "normal"
          ? document.getElementById("humanFeedback").value
          : null,
        artifact_content: artifactContent,
        llm_format_mode: "interrupt",
        resume_after_approve: true
      };
      clearPromptPanel("正在处理人工确认请求...");
      output.textContent = action === "approve" ? "已确认，正在继续生成..." : "正在保存修改...";
      try {
        if (action === "approve") {
          startRuntimePolling(lastJobId);
        }
        const response = await fetch(`/api/v1/jobs/${encodeURIComponent(lastJobId)}/human-confirmations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        output.textContent = JSON.stringify(data, null, 2);
        await loadRuntimeStatus(lastJobId);
        await loadPrompts(lastJobId);
        if (!response.ok) {
          return;
        }
        if (data.llm_repair_available) {
          renderRepairPanel(data);
        } else if (data.llm_retry_available) {
          renderRuntimePanel(data);
        } else if (data.human_confirmation_required && data.human_confirmation_point) {
          await renderHumanConfirmationPanel(data);
        } else {
          clearRepairPanel();
        }
      } catch (error) {
        output.textContent = String(error);
      } finally {
        stopRuntimePolling();
        await loadRuntimeStatus(lastJobId);
      }
    }

    function createClientJobId(prefix = "job") {
      const randomPart = window.crypto && window.crypto.randomUUID
        ? window.crypto.randomUUID().replaceAll("-", "").slice(0, 12)
        : `${Date.now()}${Math.floor(Math.random() * 10000)}`;
      return `${prefix}_${randomPart}`;
    }

    async function submitJob(
      llmFormatMode = "interrupt",
      jobId = null,
      resumeFromCheckpoint = false,
      forceRestart = false
    ) {
      submit.disabled = true;
      clearRepairPanel();
      clearPromptPanel("正在等待本次任务的 LLM prompt trace...");
      output.textContent = llmFormatMode === "auto_repair"
        ? "已确认修复，正在从检查点继续，并把失败节点的原始输出、错误信息和目标 schema 提交给 LLM 修复..."
        : (resumeFromCheckpoint ? "正在从最后成功节点继续，请稍候..." : "正在生成，请稍候...");
      try {
        const payload = {
          user_request: document.getElementById("request").value,
          execution_options: collectOptions(),
          llm_format_mode: llmFormatMode,
          resume_from_checkpoint: resumeFromCheckpoint,
          force_restart: forceRestart
        };
        const chosenJobId = jobId || jobIdInput.value.trim() || createClientJobId("job");
        payload.job_id = chosenJobId;
        startRuntimePolling(chosenJobId);
        lastPayload = payload;
        const response = await fetch("/api/v1/jobs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        lastJobId = data.job_id;
        jobIdInput.value = data.job_id;
        await loadRuntimeStatus(lastJobId);
        output.textContent = JSON.stringify(data, null, 2);
        await loadPrompts(lastJobId);
        if (data.llm_repair_available) {
          renderRepairPanel(data);
        } else if (data.llm_retry_available) {
          renderRuntimePanel(data);
        } else if (data.human_confirmation_required && data.human_confirmation_point) {
          await renderHumanConfirmationPanel(data);
        }
      } catch (error) {
        output.textContent = String(error);
      } finally {
        stopRuntimePolling();
        await loadRuntimeStatus(lastJobId);
        submit.disabled = false;
      }
    }

    async function loadPrompts(jobId = lastJobId) {
      if (!jobId) {
        clearPromptPanel();
        return;
      }
      try {
        const response = await fetch(`/api/v1/jobs/${encodeURIComponent(jobId)}/llm-prompts`);
        if (!response.ok) {
          clearPromptPanel("暂未找到该任务的 prompt trace。");
          return;
        }
        const data = await response.json();
        if (!data.prompts || data.prompts.length === 0) {
          clearPromptPanel("本次任务没有可显示的 LLM prompt trace。若使用 fake LLM 或关闭 trace，可能不会产生文件。");
          return;
        }
        promptHint.textContent = `共 ${data.prompts.length} 条 prompt trace，点击任意一条查看完整 system/user prompt。`;
        promptList.innerHTML = data.prompts.map(item => `
          <button type="button" data-trace-id="${escapeHtml(item.trace_id)}" title="${escapeHtml(item.path || "")}">
            ${escapeHtml(item.prompt_id || item.trace_id)}
          </button>
        `).join("");
        promptList.querySelectorAll("button").forEach(button => {
          button.onclick = () => loadPromptDetail(jobId, button.dataset.traceId);
        });
      } catch (error) {
        clearPromptPanel(String(error));
      }
    }

    async function loadPromptDetail(jobId, traceId) {
      const response = await fetch(
        `/api/v1/jobs/${encodeURIComponent(jobId)}/llm-prompts/${encodeURIComponent(traceId)}`
      );
      if (!response.ok) {
        promptPreview.style.display = "block";
        promptPreview.textContent = "读取 prompt trace 失败。";
        return;
      }
      const data = await response.json();
      promptPath.style.display = "block";
      promptPath.textContent = data.path || "";
      promptPreview.style.display = "block";
      promptPreview.textContent = (data.messages || [])
        .map(message => `# ${String(message.role || "").toUpperCase()}\\n${message.content || ""}`)
        .join("\\n\\n---\\n\\n");
    }

    async function submitModuleRun(moduleName) {
      const sourceJobId = jobIdInput.value.trim() || lastJobId;
      if (!sourceJobId) {
        output.textContent = "请先填写源任务 ID，或先运行一次完整任务。";
        return;
      }
      clearRepairPanel();
      clearPromptPanel("正在等待模块运行的 LLM prompt trace...");
      output.textContent = `正在运行 ${moduleName} 模块...`;
      const endpoint = moduleName === "director"
        ? `/api/v1/jobs/${encodeURIComponent(sourceJobId)}/director-runs`
        : (
            moduleName === "audiovisual"
              ? `/api/v1/jobs/${encodeURIComponent(sourceJobId)}/audiovisual-runs`
              : `/api/v1/jobs/${encodeURIComponent(sourceJobId)}/art-runs`
          );
      const outputJobId = createClientJobId(
        moduleName === "director"
          ? `${sourceJobId}_director`
          : (moduleName === "audiovisual" ? `${sourceJobId}_av` : `${sourceJobId}_art`)
      );
      let payload = null;
      if (moduleName === "director") {
        payload = {
            output_job_id: outputJobId,
            episode_script_artifact_id:
              document.getElementById("moduleEpisodeScript").value.trim() || null,
            llm_format_mode: "interrupt"
          };
      } else if (moduleName === "audiovisual") {
        payload = {
            output_job_id: outputJobId,
            performance_direction_artifact_id:
              document.getElementById("modulePerformanceDirection").value.trim() || null,
            llm_format_mode: "interrupt"
          };
      } else {
        payload = {
          output_job_id: outputJobId,
          scene_breakdown_job_id:
            document.getElementById("moduleSceneBreakdownJob").value.trim() || null,
          scene_breakdown_artifact_id:
            document.getElementById("moduleSceneBreakdown").value.trim() || null,
          audiovisual_enhanced_shot_list_job_id:
            document.getElementById("moduleAvEnhancedJob").value.trim() || null,
          audiovisual_enhanced_shot_list_artifact_id:
            document.getElementById("moduleAvEnhanced").value.trim() || null,
          character_bible_job_id:
            document.getElementById("moduleCharacterBibleJob").value.trim() || null,
          character_bible_artifact_id:
            document.getElementById("moduleCharacterBible").value.trim() || null,
          llm_format_mode: "interrupt"
        };
      }
      try {
        startRuntimePolling(outputJobId);
        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        output.textContent = JSON.stringify(data, null, 2);
        if (!response.ok) {
          return;
        }
        lastJobId = data.job_id;
        jobIdInput.value = data.job_id;
        await loadRuntimeStatus(data.job_id);
        await loadPrompts(data.job_id);
      } catch (error) {
        output.textContent = String(error);
      } finally {
        stopRuntimePolling();
        await loadRuntimeStatus(lastJobId);
      }
    }

    renderOptions();
    submit.onclick = () => submitJob("interrupt");
    document.getElementById("resumeJob").onclick = () => {
      const chosenJobId = jobIdInput.value.trim();
      if (!chosenJobId) {
        output.textContent = "请先填写要继续的任务 ID。";
        return;
      }
      submitJob("interrupt", chosenJobId, true);
    };
    document.getElementById("restartJob").onclick = () => {
      const chosenJobId = jobIdInput.value.trim();
      if (!chosenJobId) {
        output.textContent = "请先填写要强制重跑的任务 ID。";
        return;
      }
      submitJob("interrupt", chosenJobId, false, true);
    };
    document.getElementById("full").onclick = () => setAll(true);
    document.getElementById("fast").onclick = setFastDraft;
    refreshPrompts.onclick = () => loadPrompts();
    runDirectorModule.onclick = () => submitModuleRun("director");
    runAvModule.onclick = () => submitModuleRun("audiovisual");
    runArtModule.onclick = () => submitModuleRun("art");
  </script>
</body>
</html>
"""

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    return app


app = create_app()
