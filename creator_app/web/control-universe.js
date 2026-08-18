const TOKEN_STORAGE_KEY = "cknexus_access_token";
const SESSION_ID = "control-universe";

const state = {
  overview: null,
  graph: null,
  evidence: [],
  events: [],
  lastSeq: 0,
  selectedScale: 12,
  selectedAgent: null,
  activeView: "workspace",
  consoleFilter: "ALL",
  streamAbort: null,
};

const elements = {
  sourceSha: document.querySelector("#source-sha"),
  environmentName: document.querySelector("#environment-name"),
  productionStatus: document.querySelector("#production-status"),
  ledgerStatus: document.querySelector("#ledger-status"),
  dbState: document.querySelector("#db-state"),
  pgState: document.querySelector("#pg-state"),
  redisState: document.querySelector("#redis-state"),
  evidenceState: document.querySelector("#evidence-state"),
  agnesRuntimeState: document.querySelector("#agnes-runtime-state"),
  modelSummary: document.querySelector("#model-summary"),
  evidenceCount: document.querySelector("#evidence-count"),
  providerList: document.querySelector("#provider-list"),
  telemetryGrid: document.querySelector("#telemetry-grid"),
  controlCapabilityCopy: document.querySelector("#control-capability-copy"),
  metricMemory: document.querySelector("#metric-memory"),
  metricProviders: document.querySelector("#metric-providers"),
  metricAgents: document.querySelector("#metric-agents"),
  metricEvents: document.querySelector("#metric-events"),
  scaleInspector: document.querySelector("#scale-inspector"),
  graphKind: document.querySelector("#graph-kind"),
  graphChain: document.querySelector("#graph-chain"),
  evidenceChain: document.querySelector("#evidence-chain"),
  evidenceInspector: document.querySelector("#evidence-inspector"),
  consoleOutput: document.querySelector("#console-output"),
  streamState: document.querySelector("#stream-state"),
  eventCursor: document.querySelector("#event-cursor"),
  officeStage: document.querySelector("#office-stage"),
  officeEventCopy: document.querySelector("#office-event-copy"),
  chatAgentList: document.querySelector("#chat-agent-list"),
  chatThread: document.querySelector("#chat-thread"),
  chatForm: document.querySelector("#chat-form"),
  chatPrompt: document.querySelector("#chat-prompt"),
  chatSend: document.querySelector("#chat-send"),
  refreshButton: document.querySelector("#refresh-button"),
  commandOpen: document.querySelector("#command-open"),
  commandPalette: document.querySelector("#command-palette"),
  commandInput: document.querySelector("#command-input"),
  commandResults: document.querySelector("#command-results"),
  toast: document.querySelector("#toast"),
};

const scaleMeta = {
  12: ["ระบบ", "SYSTEM", "ภาพรวมบริการ Runtime, health และ evidence authority"],
  11: ["เวิร์กสเปซ", "WORKSPACE", "ขอบเขต Tenant / Workspace / Identity"],
  10: ["ภารกิจ", "MISSION", "AGNES orchestration และเป้าหมายระดับสูง"],
  9: ["งาน", "TASK", "Task-scoped state ต้องมาจาก task authority เมื่อมี adapter"],
  8: ["เวิร์กโฟลว์", "WORKFLOW", "Graph, dependency และ checkpoint ของ workflow"],
  7: ["สภาเอเจนต์", "COUNCIL", "การแบ่งบทบาทและ policy-bound handoff"],
  6: ["เอเจนต์", "AGENT", "Agent identity, role และ runtime state"],
  5: ["โมเดล", "MODEL", "Provider, model availability, circuit state และ capabilities"],
  4: ["เครื่องมือ", "TOOL", "Tool Gateway, integrations และ capability enforcement"],
  3: ["โหนด", "NODE", "หน่วย execution ย่อยของ workflow"],
  2: ["การตรวจสอบ", "VERIFY", "Policy, integrity, assertions และ verifier result"],
  1: ["หลักฐาน", "EVIDENCE", "Hash-chained record, provenance และ timestamp"],
};

function sessionGet(key) {
  try {
    return window.sessionStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function sessionSet(key, value) {
  try {
    if (value) window.sessionStorage.setItem(key, value);
    else window.sessionStorage.removeItem(key);
  } catch {
    // Browsers may disable sessionStorage in restricted contexts.
  }
}

function accessToken() {
  return sessionGet(TOKEN_STORAGE_KEY);
}

function requestHeaders(json = false) {
  const headers = {};
  if (json) headers["Content-Type"] = "application/json";
  const token = accessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => elements.toast.classList.remove("visible"), 3600);
}

function requestToken() {
  const value = window.prompt("CK-NEXUS access token");
  if (!value) return false;
  sessionSet(TOKEN_STORAGE_KEY, value.trim());
  return true;
}

async function api(path, options = {}, retryAuth = true) {
  const merged = {
    ...options,
    headers: {
      ...requestHeaders(Boolean(options.body)),
      ...(options.headers || {}),
    },
  };
  const response = await fetch(path, merged);
  const payload = await response.json().catch(() => ({}));
  if (response.status === 401 && retryAuth && requestToken()) {
    return api(path, options, false);
  }
  if (!response.ok) {
    const detail = payload.detail || payload;
    const error = new Error(detail.message || detail.error || `HTTP ${response.status}`);
    error.status = response.status;
    error.code = detail.error || "REQUEST_FAILED";
    throw error;
  }
  return payload;
}

function setTextState(element, value) {
  const text = String(value ?? "UNKNOWN");
  element.textContent = text;
  element.classList.remove("status-pass", "status-warn", "status-unknown");
  if (["READY", "PASS", "VALID", "AVAILABLE", "VERIFIED"].includes(text)) {
    element.classList.add("status-pass");
  } else if (["NOT_REQUIRED", "UNKNOWN", "NOT_COLLECTED"].includes(text)) {
    element.classList.add("status-unknown");
  } else if (text.includes("NO-GO") || text.includes("UNAVAILABLE") || text.includes("FAILED")) {
    element.classList.add("status-warn");
  }
}

function shortSha(value) {
  if (!value || value === "UNKNOWN") return "UNKNOWN";
  return value.length > 12 ? `${value.slice(0, 12)}…` : value;
}

function renderOverview() {
  const data = state.overview;
  if (!data) return;

  elements.sourceSha.textContent = shortSha(data.source_identity.sha);
  elements.sourceSha.title = data.source_identity.sha;
  elements.environmentName.textContent = data.product.environment || "UNKNOWN";
  elements.productionStatus.textContent = data.production.status;

  const ledgerStatus = data.evidence.valid ? "VALID" : "FAILED";
  setTextState(elements.ledgerStatus, ledgerStatus);
  setTextState(elements.dbState, data.runtime.database);
  setTextState(elements.pgState, data.runtime.postgres_binding);
  setTextState(elements.redisState, data.runtime.redis_binding);
  setTextState(elements.evidenceState, ledgerStatus);

  const inference = data.governance.inference || {};
  setTextState(
    elements.agnesRuntimeState,
    inference.ready ? `READY / ${inference.provider || "PROVIDER"}` : "BLOCKED",
  );

  const availableProviders = data.providers.filter(
    (item) => item.available && !item.circuit_open,
  );
  elements.modelSummary.textContent = availableProviders.length
    ? `${availableProviders.length} AVAILABLE`
    : "NO READY PROVIDER";
  elements.evidenceCount.textContent = `${data.evidence.entries} RECORDS`;

  renderProviders(data.providers);
  renderTelemetry(data.telemetry);
  renderAgents(data.agents);

  const caps = data.capabilities;
  const controlEnabled = caps.pause_task || caps.resume_task || caps.cancel_task || caps.retry_node;
  elements.controlCapabilityCopy.textContent = controlEnabled
    ? "Task-control adapter พร้อมใช้งานสำหรับคำสั่งที่ Backend ประกาศรองรับ"
    : `${caps.reason} ปุ่ม mutation ต้อง fail closed จนกว่าจะ bind adapter จริง`;

  const rss = data.telemetry.memory_max_rss_kb;
  elements.metricMemory.textContent = rss == null ? "—" : `${Math.round(rss / 1024)} MB`;
  elements.metricProviders.textContent = String(data.providers.length);
  elements.metricAgents.textContent = String(data.agents.length);
  elements.metricEvents.textContent = String(state.events.length);
}

function renderProviders(providers) {
  elements.providerList.replaceChildren();
  if (!providers.length) {
    elements.providerList.textContent = "ไม่พบ Provider Status";
    return;
  }
  providers.forEach((provider) => {
    const row = document.createElement("div");
    row.className = "provider-item";
    const label = document.createElement("span");
    const dot = document.createElement("i");
    dot.className = `status-dot ${provider.available && !provider.circuit_open ? "ready" : "blocked"}`;
    label.append(dot, document.createTextNode(` ${provider.name}`));
    const status = document.createElement("strong");
    status.textContent = provider.available && !provider.circuit_open ? "AVAILABLE" : "BLOCKED";
    row.append(label, status);
    elements.providerList.append(row);
  });
}

function renderTelemetry(telemetry) {
  elements.telemetryGrid.replaceChildren();
  const metrics = [
    ["Memory max RSS", telemetry.memory_max_rss_kb, "KB", telemetry.availability.memory_max_rss_kb],
    ["CPU", telemetry.cpu_percent, "%", telemetry.availability.cpu_percent],
    ["GPU", telemetry.gpu_percent, "%", telemetry.availability.gpu_percent],
    ["Tokens / sec", telemetry.tokens_per_second, "t/s", telemetry.availability.tokens_per_second],
    ["Estimated cost", telemetry.estimated_cost_usd, "USD", telemetry.availability.estimated_cost_usd],
  ];
  metrics.forEach(([name, value, unit, availability]) => {
    const row = document.createElement("div");
    row.className = "telemetry-item";
    const label = document.createElement("span");
    label.textContent = name;
    const strong = document.createElement("strong");
    strong.textContent = value == null ? availability : `${value} ${unit}`;
    row.append(label, strong);
    elements.telemetryGrid.append(row);
  });
}

function renderAgents(agents) {
  const agentNodes = document.querySelectorAll("[data-agent-index]");
  agentNodes.forEach((node) => {
    const index = Number(node.dataset.agentIndex);
    const agent = agents[index];
    if (!agent) {
      node.querySelector("strong").textContent = "UNBOUND";
      node.querySelector("small").textContent = "NO RUNTIME RECORD";
      return;
    }
    node.querySelector("strong").textContent = agent.name.toUpperCase();
    node.querySelector("small").textContent = agent.runtime_state;
  });

  elements.chatAgentList.replaceChildren();
  agents.forEach((agent, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.agentId = agent.id;
    const name = document.createElement("strong");
    name.textContent = agent.name;
    const description = document.createElement("small");
    description.textContent = agent.description;
    button.append(name, description);
    button.addEventListener("click", () => selectChatAgent(agent, button));
    elements.chatAgentList.append(button);
    if (index === 0 && !state.selectedAgent) selectChatAgent(agent, button);
  });
}

function selectChatAgent(agent, button) {
  state.selectedAgent = agent;
  elements.chatAgentList.querySelectorAll("button").forEach((item) => {
    item.classList.toggle("active", item === button);
  });
}

function switchView(name) {
  state.activeView = name;
  document.querySelectorAll("[data-view-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.viewPanel === name);
  });
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === name);
  });
  if (name === "evidence") loadEvidence();
  if (name === "graph") loadGraph();
}

function selectScale(scale) {
  state.selectedScale = scale;
  document.querySelectorAll("#scale-list button").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.scale) === scale);
  });
  document.querySelectorAll("[data-scale]").forEach((node) => {
    if (node.matches("#scale-list button")) return;
    node.classList.toggle("scale-highlight", Number(node.dataset.scale) === scale);
  });
  const [thai, english, description] = scaleMeta[scale];
  elements.scaleInspector.innerHTML = `
    <span class="label">ระดับที่เลือก / SELECTED SCALE</span>
    <strong>${String(scale).padStart(2, "0")} / ${english}</strong>
    <p>${thai}: ${description}</p>
  `;
}

function iconForType(type) {
  const map = {
    system: "i-system",
    decision: "i-decision",
    workflow: "i-graph",
    agent: "i-agent",
    model: "i-model",
    tool: "i-tool",
    node: "i-pulse",
    verification: "i-verify",
    evidence: "i-evidence",
  };
  return map[type] || "i-pulse";
}

function renderGraph() {
  const graph = state.graph;
  if (!graph) return;
  elements.graphKind.textContent = graph.authoritative_task_graph
    ? graph.graph_kind
    : `${graph.graph_kind} / NOT AUTHORITATIVE TASK GRAPH`;
  elements.graphChain.replaceChildren();
  graph.nodes.forEach((node) => {
    const article = document.createElement("article");
    article.className = `graph-node state-${String(node.state).toLowerCase()}`;
    article.dataset.scale = String(node.scale);
    article.innerHTML = `
      <svg><use href="#${iconForType(node.type)}"></use></svg>
      <strong>${node.id.toUpperCase()}</strong>
      <span>${node.type}</span>
      <small>SCALE ${String(node.scale).padStart(2, "0")} · ${node.state}</small>
    `;
    article.addEventListener("click", () => selectScale(Number(node.scale)));
    elements.graphChain.append(article);
  });
}

function formatTimestamp(value) {
  if (!value) return "UNKNOWN_TIME";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("th-TH", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    fractionalSecondDigits: 3,
    hour12: false,
  }).format(date);
}

function eventCategory(event) {
  const type = String(event.event_type || "").toLowerCase();
  if (type.includes("approval") || type.includes("policy")) return "approval";
  if (type.includes("evidence") || type.includes("ledger") || event.evidence_ref) return "evidence";
  return "execution";
}

function renderConsole() {
  const filtered = state.events.filter((event) => {
    if (state.consoleFilter === "ALL") return true;
    return eventCategory(event) === state.consoleFilter;
  });
  if (!filtered.length) {
    elements.consoleOutput.textContent = "ยังไม่มี Event ที่ตรงกับตัวกรองนี้";
  } else {
    elements.consoleOutput.textContent = filtered
      .slice(-300)
      .map((event) => {
        const time = formatTimestamp(event.timestamp);
        const seq = String(event.seq).padStart(5, "0");
        const category = eventCategory(event).toUpperCase();
        return `${time} [${seq}] [${category}] ${event.event_type} task=${event.task_id} run=${event.run_id}`;
      })
      .join("\n");
    elements.consoleOutput.scrollTop = elements.consoleOutput.scrollHeight;
  }
  elements.eventCursor.textContent = `SEQ ${state.lastSeq}`;
  elements.metricEvents.textContent = String(state.events.length);
}

function renderEvidence() {
  elements.evidenceChain.replaceChildren();
  if (!state.evidence.length) {
    elements.evidenceChain.textContent = "Ledger ยังไม่มี record";
    return;
  }
  state.evidence.forEach((record) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "evidence-record";
    const seq = document.createElement("b");
    seq.textContent = `#${String(record.sequence).padStart(4, "0")}`;
    const copy = document.createElement("span");
    const type = document.createElement("span");
    type.textContent = record.event_type || "ledger.record";
    const hash = document.createElement("small");
    hash.textContent = `sha256:${String(record.hash || "UNKNOWN").slice(0, 18)}…`;
    copy.append(type, hash);
    const time = document.createElement("small");
    time.textContent = formatTimestamp(record.at);
    button.append(seq, copy, time);
    button.addEventListener("click", () => inspectEvidence(record, button));
    elements.evidenceChain.append(button);
  });
}

function inspectEvidence(record, button) {
  elements.evidenceChain.querySelectorAll(".evidence-record").forEach((item) => {
    item.classList.toggle("active", item === button);
  });
  elements.evidenceInspector.innerHTML = `
    <span class="label">รายละเอียดหลักฐาน / RECORD INSPECTOR</span>
    <pre>${escapeHtml(JSON.stringify(record, null, 2))}</pre>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function applyOfficeEvent(event) {
  const type = String(event.event_type || "").toLowerCase();
  document.querySelectorAll(".office-room").forEach((room) => {
    room.classList.remove("event-active", "event-evidence");
  });
  elements.officeStage.classList.remove("event-flow");

  let target = "core";
  if (type.includes("tool")) target = "tool";
  else if (type.includes("verify") || type.includes("review")) target = "verify";
  else if (type.includes("evidence") || type.includes("ledger")) target = "evidence";
  else if (type.includes("research")) target = "research";
  else if (type.includes("analysis")) target = "analysis";
  else if (type.includes("build") || type.includes("patch")) target = "builder";

  const room = document.querySelector(`[data-office="${target}"]`);
  if (room) {
    room.classList.add(target === "evidence" ? "event-evidence" : "event-active");
  }
  if (type.includes("tool") || type.includes("handoff") || type.includes("execution")) {
    void elements.officeStage.offsetWidth;
    elements.officeStage.classList.add("event-flow");
  }
  elements.officeEventCopy.textContent = `${formatTimestamp(event.timestamp)} · ${event.event_type} · SEQ ${event.seq}`;
}

function appendEvent(event) {
  if (!event || !Number.isFinite(Number(event.seq))) return;
  if (state.events.some((item) => item.seq === event.seq)) return;
  state.events.push(event);
  state.events.sort((a, b) => a.seq - b.seq);
  state.lastSeq = Math.max(state.lastSeq, Number(event.seq));
  renderConsole();
  applyOfficeEvent(event);
}

async function loadOverview() {
  state.overview = await api("/api/control-universe/overview");
  renderOverview();
}

async function loadGraph() {
  state.graph = await api("/api/control-universe/graph");
  renderGraph();
}

async function loadEvents() {
  const payload = await api(`/api/control-universe/events?after_seq=${state.lastSeq}&limit=500`);
  payload.events.forEach(appendEvent);
  state.lastSeq = Math.max(state.lastSeq, Number(payload.last_seq || 0));
  renderConsole();
}

async function loadEvidence() {
  const payload = await api("/api/control-universe/evidence?after_seq=0&limit=500");
  state.evidence = payload.records || [];
  renderEvidence();
  if (state.overview) {
    state.overview.evidence.entries = payload.ledger.entries;
    state.overview.evidence.valid = payload.ledger.valid;
    renderOverview();
  }
}

async function refreshAll() {
  elements.refreshButton.disabled = true;
  try {
    await Promise.all([loadOverview(), loadGraph(), loadEvidence()]);
    await loadEvents();
    showToast("รีเฟรชข้อมูล Runtime และ Evidence แล้ว");
  } catch (error) {
    showToast(error.message);
  } finally {
    elements.refreshButton.disabled = false;
  }
}

async function connectEventStream() {
  if (state.streamAbort) state.streamAbort.abort();
  const controller = new AbortController();
  state.streamAbort = controller;
  elements.streamState.textContent = "CONNECTING";
  elements.streamState.classList.remove("connected");

  try {
    let response = await fetch(`/api/control-universe/stream?after_seq=${state.lastSeq}`, {
      headers: requestHeaders(),
      signal: controller.signal,
    });
    if (response.status === 401 && requestToken()) {
      response = await fetch(`/api/control-universe/stream?after_seq=${state.lastSeq}`, {
        headers: requestHeaders(),
        signal: controller.signal,
      });
    }
    if (!response.ok || !response.body) throw new Error(`STREAM HTTP ${response.status}`);

    elements.streamState.textContent = "CONNECTED";
    elements.streamState.classList.add("connected");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (!controller.signal.aborted) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";
      chunks.forEach((chunk) => {
        const dataLine = chunk
          .split("\n")
          .find((line) => line.startsWith("data: "));
        if (!dataLine) return;
        try {
          appendEvent(JSON.parse(dataLine.slice(6)));
        } catch {
          // Ignore malformed stream frames; the reconnect catch-up endpoint remains authoritative.
        }
      });
    }
  } catch (error) {
    if (controller.signal.aborted) return;
    elements.streamState.textContent = "DISCONNECTED";
    elements.streamState.classList.remove("connected");
    try {
      await loadEvents();
    } catch {
      // Keep the last verified projection when catch-up is unavailable.
    }
    window.setTimeout(connectEventStream, 1800);
  }
}

function appendChatMessage(kind, title, content) {
  const empty = elements.chatThread.querySelector(".chat-empty");
  if (empty) empty.remove();
  const message = document.createElement("article");
  message.className = `message ${kind}`;
  const heading = document.createElement("strong");
  heading.textContent = title;
  const pre = document.createElement("pre");
  pre.textContent = content;
  message.append(heading, pre);
  elements.chatThread.append(message);
  elements.chatThread.scrollTop = elements.chatThread.scrollHeight;
}

async function submitChat(event) {
  event.preventDefault();
  const prompt = elements.chatPrompt.value.trim();
  if (!prompt || !state.selectedAgent) return;
  appendChatMessage("user", "คุณ / USER", prompt);
  elements.chatPrompt.value = "";
  elements.chatSend.disabled = true;
  elements.chatSend.textContent = "กำลังรัน";
  try {
    const run = await api("/api/runs", {
      method: "POST",
      body: JSON.stringify({
        agent_id: state.selectedAgent.id,
        prompt,
        audience: "ผู้ใช้ CK-NEXUS",
        platform: "ไม่ระบุ",
        tone: "มืออาชีพ",
        language: "ไทย",
        session_id: SESSION_ID,
      }),
    });
    appendChatMessage("assistant", `${run.agent_name || state.selectedAgent.name} / RUNTIME`, run.content);
  } catch (error) {
    appendChatMessage("assistant", "SYSTEM", `คำสั่งไม่สำเร็จ: ${error.message}`);
  } finally {
    elements.chatSend.disabled = false;
    elements.chatSend.textContent = "ส่งคำสั่ง";
  }
}

const commands = [
  ["เปิดพื้นที่ทำงานสด", "workspace", () => switchView("workspace")],
  ["เปิดแชท", "chat", () => switchView("chat")],
  ["เปิดสำนักงาน AI", "office", () => switchView("office")],
  ["เปิดกราฟงาน", "graph", () => switchView("graph")],
  ["เปิดคอนโซล", "console", () => switchView("console")],
  ["เปิดหลักฐาน", "evidence", () => switchView("evidence")],
  ["ดูระดับ Agent", "scale 06 agent", () => selectScale(6)],
  ["ดูระดับ Model", "scale 05 model", () => selectScale(5)],
  ["ดูระดับ Tool", "scale 04 tool", () => selectScale(4)],
  ["ดูระดับ Evidence", "scale 01 evidence", () => selectScale(1)],
  ["รีเฟรชข้อมูลจริง", "refresh runtime evidence", refreshAll],
];

function matchingCommands() {
  const query = elements.commandInput.value.trim().toLowerCase();
  if (!query) return commands;
  return commands.filter(([name, keywords]) => `${name} ${keywords}`.toLowerCase().includes(query));
}

function renderCommands() {
  const matches = matchingCommands();
  elements.commandResults.replaceChildren();
  matches.forEach(([name, keywords, action]) => {
    const button = document.createElement("button");
    button.type = "button";
    const title = document.createElement("span");
    title.textContent = name;
    const hint = document.createElement("small");
    hint.textContent = keywords.toUpperCase();
    button.append(title, hint);
    button.addEventListener("click", async () => {
      elements.commandPalette.close();
      await action();
    });
    elements.commandResults.append(button);
  });
}

function openCommandPalette() {
  elements.commandInput.value = "";
  renderCommands();
  if (!elements.commandPalette.open) elements.commandPalette.showModal();
  window.setTimeout(() => elements.commandInput.focus(), 30);
}

function bindEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });
  document.querySelectorAll("#scale-list button").forEach((button) => {
    button.addEventListener("click", () => selectScale(Number(button.dataset.scale)));
  });
  document.querySelectorAll(".console-filter").forEach((button) => {
    button.addEventListener("click", () => {
      state.consoleFilter = button.dataset.filter;
      document.querySelectorAll(".console-filter").forEach((item) => {
        item.classList.toggle("active", item === button);
      });
      renderConsole();
    });
  });
  elements.refreshButton.addEventListener("click", refreshAll);
  elements.chatForm.addEventListener("submit", submitChat);
  elements.commandOpen.addEventListener("click", openCommandPalette);
  elements.commandInput.addEventListener("input", renderCommands);
  elements.commandInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const command = matchingCommands()[0];
    if (!command) return;
    elements.commandPalette.close();
    command[2]();
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openCommandPalette();
    }
  });
}

async function bootstrap() {
  bindEvents();
  selectScale(12);
  try {
    await refreshAll();
    connectEventStream();
  } catch (error) {
    showToast(error.message);
  }
}

bootstrap();
