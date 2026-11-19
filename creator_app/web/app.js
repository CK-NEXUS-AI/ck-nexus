const TOKEN_STORAGE_KEY = "cknexus_access_token";
const THEME_STORAGE_KEY = "cknexus_theme";
const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)");

const state = {
  agents: [],
  selectedAgent: null,
  currentResult: null,
  runs: [],
  status: null,
  activeView: "workspace-view",
};

const elements = {
  status: document.querySelector("#system-status"),
  agentList: document.querySelector("#agent-list"),
  agentCount: document.querySelector("#agent-count"),
  agentId: document.querySelector("#agent-id"),
  prompt: document.querySelector("#prompt"),
  charCount: document.querySelector("#char-count"),
  form: document.querySelector("#brief-form"),
  runButton: document.querySelector("#run-button"),
  clearForm: document.querySelector("#clear-form"),
  selectedAgentCopy: document.querySelector("#selected-agent-copy"),
  emptyResult: document.querySelector("#empty-result"),
  resultContent: document.querySelector("#result-content"),
  resultMeta: document.querySelector("#result-meta"),
  resultText: document.querySelector("#result-text"),
  copyResult: document.querySelector("#copy-result"),
  downloadResult: document.querySelector("#download-result"),
  historyList: document.querySelector("#history-list"),
  refreshHistory: document.querySelector("#refresh-history"),
  accessToken: document.querySelector("#access-token"),
  accessGate: document.querySelector("#access-gate"),
  gateForm: document.querySelector("#gate-form"),
  gateToken: document.querySelector("#gate-token"),
  clearSessionToken: document.querySelector("#clear-session-token"),
  deleteLocalSession: document.querySelector("#delete-local-session"),
  commandPalette: document.querySelector("#command-palette"),
  commandOpen: document.querySelector("#command-open"),
  commandInput: document.querySelector("#command-input"),
  commandList: document.querySelector("#command-list"),
  metricRuns: document.querySelector("#metric-runs"),
  metricAgents: document.querySelector("#metric-agents"),
  metricMode: document.querySelector("#metric-mode"),
  metricModel: document.querySelector("#metric-model"),
  systemAppState: document.querySelector("#system-app-state"),
  systemAiState: document.querySelector("#system-ai-state"),
  systemDbState: document.querySelector("#system-db-state"),
  systemGateState: document.querySelector("#system-gate-state"),
  toast: document.querySelector("#toast"),
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
    // Private browser contexts may disable storage; the in-form value still works.
  }
}

function localGet(key) {
  try {
    return window.localStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function localSet(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // The selected theme remains active for this page even if storage is unavailable.
  }
}

function accessToken() {
  return elements.accessToken.value.trim() || sessionGet(TOKEN_STORAGE_KEY);
}

function requestHeaders(includeJson = false) {
  const value = {};
  if (includeJson) value["Content-Type"] = "application/json";
  const token = accessToken();
  if (token) value.Authorization = `Bearer ${token}`;
  return value;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || payload;
    const error = new Error(detail.message || detail.error || `HTTP ${response.status}`);
    error.status = response.status;
    error.code = detail.error || "REQUEST_FAILED";
    throw error;
  }
  return payload;
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("visible");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => {
    elements.toast.classList.remove("visible");
  }, 3400);
}

function setConnectionState(element, text, connectionClass) {
  element.textContent = text;
  element.classList.remove("checking", "linked", "disconnected");
  element.classList.add(connectionClass);
}

function showAccessGate() {
  if (!elements.accessGate.open) {
    elements.accessGate.showModal();
  }
  window.setTimeout(() => elements.gateToken.focus(), 50);
}

function handleApiError(error) {
  if (error.status === 401) showAccessGate();
  showToast(error.message);
}

function renderAgents() {
  elements.agentList.replaceChildren();
  elements.agentCount.textContent = String(state.agents.length).padStart(2, "0");
  animateNumber(elements.metricAgents, state.agents.length);

  state.agents.forEach((agent) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "agent-card";
    button.dataset.agentId = agent.id;
    button.setAttribute("aria-pressed", "false");

    const code = document.createElement("span");
    code.className = "agent-icon";
    code.textContent = agent.icon;

    const copy = document.createElement("span");
    const name = document.createElement("strong");
    name.textContent = agent.name;
    const description = document.createElement("small");
    description.textContent = agent.description;
    copy.append(name, description);

    const action = document.createElement("span");
    action.className = "agent-action";
    action.textContent = "SELECT";

    button.append(code, copy, action);
    button.addEventListener("click", () => selectAgent(agent));
    elements.agentList.append(button);
  });
}

function selectAgent(agent) {
  state.selectedAgent = agent;
  elements.agentId.value = agent.id;
  elements.selectedAgentCopy.textContent = `${agent.name} / READY`;
  elements.prompt.placeholder = agent.example;
  elements.runButton.disabled = false;

  document.querySelectorAll(".agent-card").forEach((card) => {
    const selected = card.dataset.agentId === agent.id;
    card.classList.toggle("selected", selected);
    card.setAttribute("aria-pressed", String(selected));
    const action = card.querySelector(".agent-action");
    if (action) action.textContent = selected ? "SELECTED" : "SELECT";
  });
}

function switchView(viewId, { focus = false } = {}) {
  const target = document.getElementById(viewId);
  if (!target) return;

  state.activeView = viewId;
  document.querySelectorAll(".view-panel").forEach((panel) => {
    const active = panel.id === viewId;
    panel.classList.toggle("active", active);
    panel.setAttribute("aria-hidden", String(!active));
  });
  document.querySelectorAll(".nav-link").forEach((button) => {
    button.classList.toggle("active", button.dataset.viewTarget === viewId);
  });

  window.scrollTo({ top: 0, behavior: REDUCED_MOTION.matches ? "auto" : "smooth" });
  if (viewId === "stream-view") loadHistory();
  if (focus) target.focus({ preventScroll: true });
}

function renderResult(run, { reveal = true } = {}) {
  state.currentResult = run;
  elements.emptyResult.classList.add("hidden");
  elements.resultContent.classList.remove("hidden");
  elements.copyResult.disabled = false;
  elements.downloadResult.disabled = false;
  elements.resultText.textContent = run.content;
  elements.resultMeta.replaceChildren();

  [run.agent_name, run.platform, run.language, `${run.duration_ms} MS`, run.mode].forEach((item) => {
    const label = document.createElement("span");
    label.textContent = item;
    elements.resultMeta.append(label);
  });

  if (reveal) {
    switchView("workspace-view");
    window.setTimeout(() => {
      document.querySelector("#result-panel").scrollIntoView({
        behavior: REDUCED_MOTION.matches ? "auto" : "smooth",
        block: "start",
      });
    }, 80);
  }
}

function formatTime(value) {
  return new Intl.DateTimeFormat("th-TH", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function renderHistory(runs) {
  state.runs = runs;
  animateNumber(elements.metricRuns, runs.length);
  elements.historyList.replaceChildren();
  if (!runs.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "NO RECORDS IN THIS SESSION";
    elements.historyList.append(empty);
    return;
  }

  runs.forEach((run) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "history-item";

    const copy = document.createElement("span");
    const prompt = document.createElement("strong");
    prompt.textContent = run.prompt;
    const meta = document.createElement("small");
    meta.textContent = `${run.agent_name} / ${run.platform} / ${run.mode} / [ COMPLETED ]`;
    copy.append(prompt, meta);

    const time = document.createElement("time");
    time.dateTime = run.created_at;
    time.textContent = formatTime(run.created_at);

    item.append(copy, time);
    item.addEventListener("click", () => renderResult(run));
    elements.historyList.append(item);
  });
}

function animateNumber(element, target) {
  const finalValue = Math.max(0, Number(target) || 0);
  const from = Number(element.dataset.value || 0);
  element.dataset.value = String(finalValue);

  if (REDUCED_MOTION.matches || from === finalValue) {
    element.textContent = String(finalValue).padStart(2, "0");
    return;
  }

  const started = performance.now();
  const duration = 620;
  const tick = (now) => {
    const progress = Math.min(1, (now - started) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.round(from + (finalValue - from) * eased);
    element.textContent = String(value).padStart(2, "0");
    if (progress < 1) window.requestAnimationFrame(tick);
  };
  window.requestAnimationFrame(tick);
}

async function loadStatus() {
  try {
    const status = await api("/api/status");
    state.status = status;
    setConnectionState(elements.systemAppState, "[ LINKED ]", "linked");
    setConnectionState(
      elements.systemDbState,
      status.database_ready ? "[ LINKED ]" : "[ DISCONNECTED ]",
      status.database_ready ? "linked" : "disconnected",
    );
    setConnectionState(
      elements.systemGateState,
      status.access_required ? "[ REQUIRED ]" : "[ OPEN ]",
      "linked",
    );

    if (status.mode === "mock") {
      setConnectionState(elements.status, "[ DEMO LINKED ]", "linked");
      setConnectionState(elements.systemAiState, "[ DEMO LINKED ]", "linked");
      setConnectionState(elements.metricMode, "[ DEMO LINKED ]", "linked");
    } else if (status.mode === "openai") {
      setConnectionState(elements.status, "[ LIVE LINKED ]", "linked");
      setConnectionState(elements.systemAiState, "[ LIVE LINKED ]", "linked");
      setConnectionState(elements.metricMode, "[ LIVE LINKED ]", "linked");
    } else {
      setConnectionState(elements.status, "[ LIVE DISCONNECTED ]", "disconnected");
      setConnectionState(elements.systemAiState, "[ LIVE DISCONNECTED ]", "disconnected");
      setConnectionState(elements.metricMode, "[ LIVE DISCONNECTED ]", "disconnected");
    }
    elements.metricModel.textContent = `MODEL / ${status.model.toUpperCase()}`;
    return status;
  } catch (error) {
    [elements.status, elements.systemAppState, elements.systemAiState, elements.systemDbState].forEach(
      (element) => setConnectionState(element, "[ DISCONNECTED ]", "disconnected"),
    );
    setConnectionState(elements.metricMode, "[ DISCONNECTED ]", "disconnected");
    elements.metricModel.textContent = "MODEL / UNAVAILABLE";
    handleApiError(error);
    return null;
  }
}

async function loadAgents() {
  try {
    const payload = await api("/api/agents", { headers: requestHeaders() });
    state.agents = payload.agents;
    renderAgents();
    if (state.agents.length && !state.selectedAgent) selectAgent(state.agents[0]);
    return true;
  } catch (error) {
    handleApiError(error);
    return false;
  }
}

async function loadHistory() {
  try {
    const sessionId = document.querySelector("#session-id").value.trim();
    const query = new URLSearchParams({ session_id: sessionId, limit: "20" });
    const runs = await api(`/api/runs?${query}`, { headers: requestHeaders() });
    renderHistory(runs);
    return true;
  } catch (error) {
    handleApiError(error);
    return false;
  }
}

function autoTheme() {
  const hour = new Date().getHours();
  if (hour >= 19 || hour < 6) return "midnight";
  if (hour >= 17) return "aurora";
  return "alabaster";
}

function setTheme(theme, { persist = true } = {}) {
  const allowed = new Set(["midnight", "alabaster", "aurora"]);
  const nextTheme = allowed.has(theme) ? theme : autoTheme();
  document.documentElement.dataset.theme = nextTheme;
  document.querySelectorAll(".theme-button").forEach((button) => {
    const active = button.dataset.themeValue === nextTheme;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  if (persist) localSet(THEME_STORAGE_KEY, nextTheme);
}

const commands = [
  {
    name: "OPEN WORKSPACE",
    keywords: "workspace creator brief generate home",
    hint: "VIEW / 01",
    run: () => switchView("workspace-view"),
  },
  {
    name: "OPEN DATA STREAM",
    keywords: "stream history metrics output",
    hint: "VIEW / 02",
    run: () => switchView("stream-view"),
  },
  {
    name: "OPEN SYSTEM MATRIX",
    keywords: "system settings control status",
    hint: "VIEW / 03",
    run: () => switchView("system-view"),
  },
  {
    name: "FOCUS CREATIVE BRIEF",
    keywords: "brief prompt type create",
    hint: "ACTION",
    run: () => {
      switchView("workspace-view");
      window.setTimeout(() => elements.prompt.focus(), 120);
    },
  },
  {
    name: "THEME / DEEP MIDNIGHT",
    keywords: "theme midnight dark",
    hint: "ENVIRONMENT",
    run: () => setTheme("midnight"),
  },
  {
    name: "THEME / CLEAN ALABASTER",
    keywords: "theme alabaster light",
    hint: "ENVIRONMENT",
    run: () => setTheme("alabaster"),
  },
  {
    name: "THEME / CYBER AURORA",
    keywords: "theme aurora cyber accent",
    hint: "ENVIRONMENT",
    run: () => setTheme("aurora"),
  },
  {
    name: "REFRESH DATA STREAM",
    keywords: "refresh reload status history",
    hint: "ACTION",
    run: async () => {
      await Promise.all([loadStatus(), loadAgents(), loadHistory()]);
      showToast("DATA STREAM REFRESHED");
    },
  },
];

function filteredCommands() {
  const query = elements.commandInput.value.trim().toLowerCase();
  if (!query) return commands;
  return commands.filter((command) => `${command.name} ${command.keywords}`.toLowerCase().includes(query));
}

function runCommand(command) {
  elements.commandPalette.close();
  elements.commandInput.value = "";
  command.run();
}

function renderCommands() {
  const matches = filteredCommands();
  elements.commandList.replaceChildren();
  if (!matches.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "NO MATCHING COMMAND";
    elements.commandList.append(empty);
    return;
  }

  matches.forEach((command, index) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `command-item${index === 0 ? " active" : ""}`;
    const name = document.createElement("strong");
    name.textContent = command.name;
    const hint = document.createElement("small");
    hint.textContent = command.hint;
    item.append(name, hint);
    item.addEventListener("click", () => runCommand(command));
    elements.commandList.append(item);
  });
}

function openCommandPalette() {
  renderCommands();
  if (!elements.commandPalette.open) elements.commandPalette.showModal();
  window.setTimeout(() => elements.commandInput.focus(), 40);
}

function activateMotion() {
  if (REDUCED_MOTION.matches || !window.matchMedia("(pointer: fine)").matches) return;

  document.querySelectorAll(".magnetic").forEach((element) => {
    element.addEventListener("pointermove", (event) => {
      const rect = element.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width - 0.5) * 9;
      const y = ((event.clientY - rect.top) / rect.height - 0.5) * 7;
      element.style.setProperty("--magnetic-x", `${x.toFixed(2)}px`);
      element.style.setProperty("--magnetic-y", `${y.toFixed(2)}px`);
    });
    element.addEventListener("pointerleave", () => {
      element.style.setProperty("--magnetic-x", "0px");
      element.style.setProperty("--magnetic-y", "0px");
    });
  });

  let frame = 0;
  document.addEventListener("pointermove", (event) => {
    if (frame) return;
    frame = window.requestAnimationFrame(() => {
      const x = ((event.clientX / window.innerWidth) - 0.5) * 28;
      const y = ((event.clientY / window.innerHeight) - 0.5) * 22;
      document.documentElement.style.setProperty("--pointer-x", `${x.toFixed(2)}px`);
      document.documentElement.style.setProperty("--pointer-y", `${y.toFixed(2)}px`);
      frame = 0;
    });
  });
}

function typeReveal(element) {
  if (!element || REDUCED_MOTION.matches) return;
  const text = element.textContent;
  element.setAttribute("aria-label", text);
  element.textContent = "";
  let index = 0;
  const timer = window.setInterval(() => {
    index += 1;
    element.textContent = text.slice(0, index);
    if (index >= text.length) window.clearInterval(timer);
  }, 18);
}

function bindEvents() {
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.viewTarget));
  });

  document.querySelectorAll(".theme-button").forEach((button) => {
    button.addEventListener("click", () => setTheme(button.dataset.themeValue));
  });

  elements.prompt.addEventListener("input", () => {
    elements.charCount.textContent = String(elements.prompt.value.length);
  });

  elements.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.selectedAgent) return;

    const originalLabel = elements.runButton.firstElementChild.textContent;
    elements.runButton.disabled = true;
    elements.runButton.firstElementChild.textContent = "GENERATING";

    const payload = {
      agent_id: elements.agentId.value,
      prompt: elements.prompt.value,
      audience: document.querySelector("#audience").value,
      platform: document.querySelector("#platform").value,
      tone: document.querySelector("#tone").value,
      language: document.querySelector("#language").value,
      session_id: document.querySelector("#session-id").value,
    };

    try {
      const run = await api("/api/runs", {
        method: "POST",
        headers: requestHeaders(true),
        body: JSON.stringify(payload),
      });
      renderResult(run);
      await loadHistory();
    } catch (error) {
      handleApiError(error);
    } finally {
      elements.runButton.disabled = false;
      elements.runButton.firstElementChild.textContent = originalLabel;
    }
  });

  elements.clearForm.addEventListener("click", () => {
    elements.prompt.value = "";
    elements.charCount.textContent = "0";
    elements.prompt.focus();
  });

  elements.copyResult.addEventListener("click", async () => {
    if (!state.currentResult) return;
    try {
      await navigator.clipboard.writeText(state.currentResult.content);
      showToast("OUTPUT COPIED");
    } catch {
      showToast("COPY BLOCKED BY BROWSER");
    }
  });

  elements.downloadResult.addEventListener("click", () => {
    if (!state.currentResult) return;
    const content = state.currentResult.content;
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ck-nexus-${state.currentResult.id}.txt`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    showToast("TEXT FILE EXPORTED");
  });

  elements.refreshHistory.addEventListener("click", loadHistory);
  document.querySelector("#session-id").addEventListener("change", loadHistory);

  elements.accessToken.addEventListener("change", async () => {
    const token = elements.accessToken.value.trim();
    sessionSet(TOKEN_STORAGE_KEY, token);
    await Promise.all([loadAgents(), loadHistory()]);
  });

  elements.gateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const token = elements.gateToken.value.trim();
    elements.accessToken.value = token;
    sessionSet(TOKEN_STORAGE_KEY, token);
    try {
      const payload = await api("/api/agents", { headers: requestHeaders() });
      state.agents = payload.agents;
      renderAgents();
      if (state.agents.length) selectAgent(state.agents[0]);
      await loadHistory();
      elements.gateToken.value = "";
      elements.accessGate.close();
      setConnectionState(elements.systemGateState, "[ AUTHORIZED ]", "linked");
      showToast("ACCESS GATE / AUTHORIZED");
    } catch (error) {
      sessionSet(TOKEN_STORAGE_KEY, "");
      elements.accessToken.value = "";
      elements.gateToken.select();
      handleApiError(error);
    }
  });

  elements.clearSessionToken.addEventListener("click", () => {
    sessionSet(TOKEN_STORAGE_KEY, "");
    elements.accessToken.value = "";
    elements.gateToken.value = "";
    setConnectionState(
      elements.systemGateState,
      state.status?.access_required ? "[ AUTHORIZATION REQUIRED ]" : "[ OPEN ]",
      state.status?.access_required ? "disconnected" : "linked",
    );
    if (state.status?.access_required) showAccessGate();
    showToast("SESSION TOKEN CLEARED");
  });

  elements.deleteLocalSession.addEventListener("click", async () => {
    const sessionId = document.querySelector("#session-id").value.trim();
    const approved = window.confirm(
      `ลบประวัติและ memory ของ session “${sessionId}” ออกจากเครื่องนี้หรือไม่`,
    );
    if (!approved) return;
    try {
      const payload = await api(`/api/sessions/${encodeURIComponent(sessionId)}`, {
        method: "DELETE",
        headers: requestHeaders(),
      });
      state.currentResult = null;
      elements.resultText.textContent = "";
      elements.resultContent.classList.add("hidden");
      elements.emptyResult.classList.remove("hidden");
      elements.copyResult.disabled = true;
      elements.downloadResult.disabled = true;
      renderHistory([]);
      showToast(`LOCAL SESSION DELETED / ${payload.records} RECORDS`);
    } catch (error) {
      handleApiError(error);
    }
  });

  elements.commandOpen.addEventListener("click", openCommandPalette);
  elements.commandInput.addEventListener("input", renderCommands);
  elements.commandInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      const first = filteredCommands()[0];
      if (first) runCommand(first);
    }
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (elements.commandPalette.open) elements.commandPalette.close();
      else openCommandPalette();
    }
  });

  [elements.commandPalette].forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  });
}

async function bootstrap() {
  const storedToken = sessionGet(TOKEN_STORAGE_KEY);
  elements.accessToken.value = storedToken;
  setTheme(localGet(THEME_STORAGE_KEY) || autoTheme(), { persist: false });
  bindEvents();
  activateMotion();
  document.body.classList.add("loaded");
  typeReveal(document.querySelector(".hero .eyebrow"));

  const status = await loadStatus();
  if (status?.access_required && !storedToken) {
    showAccessGate();
    return;
  }
  await Promise.all([loadAgents(), loadHistory()]);
}

bootstrap();
