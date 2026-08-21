const TOKEN_KEY = "cknexus_access_token";
const SESSION_ID = "creator-default";

const state = { status: null, agents: [], runs: [], providers: [], credentials: null, vault: null };
const $ = (selector) => document.querySelector(selector);

const el = {
  sidebar: $("#sidebar"), sidebarToggle: $("#sidebar-toggle"), globalState: $("#global-state"),
  topState: $(".top-state"), agnesState: $("#agnes-state"), agnesCopy: $("#agnes-copy"),
  runtime: $("#runtime-status"), providers: $("#provider-list"), credentials: $("#credential-status"),
  evidence: $("#evidence-list"), evidenceCount: $("#evidence-count"), conversations: $("#conversation-list"),
  runCount: $("#run-count"), agentCount: $("#agent-count"), agentSelect: $("#agent-select"),
  composer: $("#composer"), prompt: $("#prompt"), charCount: $("#char-count"), messages: $("#messages"),
  send: $("#send-btn"), refresh: $("#refresh-all"), providerRefresh: $("#provider-refresh"),
  dialog: $("#access-dialog"), accessForm: $("#access-form"), accessToken: $("#access-token"), toast: $("#toast"),
  newChat: $("#new-chat"),
};

function getToken() { try { return sessionStorage.getItem(TOKEN_KEY) || ""; } catch { return ""; } }
function setToken(value) { try { value ? sessionStorage.setItem(TOKEN_KEY, value) : sessionStorage.removeItem(TOKEN_KEY); } catch {} }
function headers(json = false) { const h = {}; if (json) h["Content-Type"] = "application/json"; const token = getToken(); if (token) h.Authorization = `Bearer ${token}`; return h; }

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || payload;
    const error = new Error(detail.message || detail.error || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return payload;
}

function toast(message) { el.toast.textContent = message; el.toast.classList.add("show"); clearTimeout(toast.timer); toast.timer = setTimeout(() => el.toast.classList.remove("show"), 2800); }
function safe(value, fallback = "—") { return value === undefined || value === null || value === "" ? fallback : String(value); }
function statusClass(ok, warning = false) { return ok ? "status-ok" : warning ? "status-warn" : "status-bad"; }
function setAgnes(mode, text) {
  const ready = mode === "ready";
  el.agnesState.classList.toggle("ready", ready);
  el.agnesState.innerHTML = `<i></i> ${ready ? "READY" : mode.toUpperCase()}`;
  el.agnesCopy.textContent = text;
}
function authError(error) { if (error.status === 401) { if (!el.dialog.open) el.dialog.showModal(); } else toast(error.message); }

function renderRuntime(status) {
  const mode = safe(status?.mode, "UNAVAILABLE");
  const database = status?.database_ready ? "READY" : "UNAVAILABLE";
  const access = status?.access_required ? "REQUIRED" : "OPEN";
  el.runtime.innerHTML = `
    <div><dt>Mode</dt><dd>${mode.toUpperCase()}</dd></div>
    <div><dt>Model</dt><dd>${safe(status?.model)}</dd></div>
    <div><dt>Database</dt><dd class="${status?.database_ready ? "status-ok" : "status-bad"}">${database}</dd></div>
    <div><dt>Access Gate</dt><dd class="${status?.access_required ? "status-warn" : "status-ok"}">${access}</dd></div>`;
  const connected = mode === "openai" || mode === "mock";
  el.topState.classList.toggle("ready", connected);
  el.globalState.textContent = connected ? (mode === "mock" ? "DEMO LINKED" : "LIVE LINKED") : "DISCONNECTED";
}

function renderProviders(payload) {
  state.providers = payload?.providers || [];
  if (!state.providers.length) { el.providers.innerHTML = `<p class="muted">ไม่พบ Provider ที่ลงทะเบียน</p>`; return; }
  el.providers.innerHTML = state.providers.slice(0, 8).map((p) => {
    const available = Boolean(p.available) && !p.circuit_open;
    const label = p.circuit_open ? "CIRCUIT OPEN" : available ? "READY" : "UNAVAILABLE";
    return `<div class="provider-row"><div><b>${safe(p.name)}</b><small>${(p.models || []).slice(0,2).join(" · ") || safe(p.kind)}</small></div><strong class="${statusClass(available, p.circuit_open)}">${label}</strong></div>`;
  }).join("");
}

function credentialCount(payload) {
  const groups = Object.values(payload?.consumers || {});
  return groups.flat().filter((item) => item && (item.configured || item.available || item.status === "configured")).length;
}
function renderCredentials() {
  const vaultOn = Boolean(state.vault?.enabled);
  const configured = credentialCount(state.credentials);
  el.credentials.innerHTML = `
    <div><dt>Secrets exposed</dt><dd class="status-ok">${state.credentials?.secrets_exposed === false ? "NO" : "UNKNOWN"}</dd></div>
    <div><dt>Vault</dt><dd class="${vaultOn ? "status-ok" : "status-warn"}">${vaultOn ? safe(state.vault.backend,"ENABLED") : "DISABLED"}</dd></div>
    <div><dt>Brokered credentials</dt><dd>${configured}</dd></div>
    <div><dt>Key material</dt><dd class="status-ok">HIDDEN</dd></div>`;
}

function renderAgents(payload) {
  state.agents = payload?.agents || [];
  el.agentCount.textContent = String(state.agents.length).padStart(2, "0");
  el.agentSelect.replaceChildren();
  state.agents.forEach((agent) => {
    const option = document.createElement("option"); option.value = agent.id; option.textContent = `${agent.name} · ${agent.description || "Specialist"}`; el.agentSelect.append(option);
  });
  if (!state.agents.length) { const option = document.createElement("option"); option.textContent = "NO SPECIALIST AVAILABLE"; el.agentSelect.append(option); }
}

function formatTime(value) { try { return new Intl.DateTimeFormat("th-TH", { dateStyle:"short", timeStyle:"short" }).format(new Date(value)); } catch { return ""; } }
function renderRuns(runs) {
  state.runs = Array.isArray(runs) ? runs : [];
  el.runCount.textContent = String(state.runs.length).padStart(2, "0");
  el.evidenceCount.textContent = String(state.runs.length).padStart(2, "0");
  if (!state.runs.length) {
    el.conversations.innerHTML = `<p class="muted">ยังไม่มีประวัติใน session นี้</p>`;
    el.evidence.innerHTML = `<p class="muted">ยังไม่มี run ใน session นี้</p>`;
    return;
  }
  el.conversations.innerHTML = state.runs.slice(0, 12).map((run, i) => `<button class="conversation-item ${i===0?"active":""}" data-run="${run.id}"><b>${safe(run.prompt,"Untitled")}</b><small>${safe(run.agent_name)} · ${formatTime(run.created_at)}</small></button>`).join("");
  el.evidence.innerHTML = state.runs.slice(0, 6).map((run) => `<div class="evidence-item"><b>${safe(run.id)}</b><small>${safe(run.agent_name)} · ${safe(run.mode)} · ${safe(run.duration_ms)} ms</small></div>`).join("");
  document.querySelectorAll("[data-run]").forEach((button) => button.addEventListener("click", () => showRun(state.runs.find((r) => String(r.id) === button.dataset.run))));
}

function appendMessage(role, text, meta = "") {
  const article = document.createElement("article"); article.className = `message ${role}`;
  const avatar = document.createElement("span"); avatar.className = "avatar"; avatar.textContent = role === "user" ? "YOU" : "AG";
  const body = document.createElement("div"); const small = document.createElement("small"); small.textContent = meta || (role === "user" ? "YOU" : "AGNES");
  const p = document.createElement("p"); p.textContent = text; body.append(small,p); article.append(avatar,body); el.messages.append(article); article.scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block:"end"});
}
function showRun(run) { if (!run) return; appendMessage("user", run.prompt, formatTime(run.created_at)); appendMessage("assistant", run.content, `${safe(run.agent_name)} · ${safe(run.mode)} · ${safe(run.duration_ms)} ms`); if (innerWidth < 761) el.sidebar.classList.remove("open"); }

async function loadPublicStatus() {
  try { state.status = await api("/api/status"); renderRuntime(state.status); }
  catch (error) { renderRuntime(null); toast(error.message); }
}
async function loadProtected() {
  try {
    const [agents, runs, providerStatus, credentials, vault] = await Promise.all([
      api("/api/agents", {headers:headers()}),
      api(`/api/runs?${new URLSearchParams({session_id:SESSION_ID,limit:"20"})}`, {headers:headers()}),
      api("/api/providers/status", {headers:headers()}),
      api("/api/security/credentials/status", {headers:headers()}),
      api("/api/security/credential-vault/status", {headers:headers()}),
    ]);
    renderAgents(agents); renderRuns(runs); renderProviders(providerStatus); state.credentials = credentials; state.vault = vault; renderCredentials();
    try { const agnes = await api("/api/agnes/status", {headers:headers()}); setAgnes("ready", `AGNES พร้อมใช้งาน · ${safe(agnes?.skills?.length || agnes?.skill_count, "runtime connected")} skills`); }
    catch { setAgnes("ready", "Runtime เชื่อมต่อแล้ว · AGNES status ไม่ได้เปิดใช้งานใน environment นี้"); }
  } catch (error) { authError(error); if (error.status !== 401) setAgnes("warning", "บางระบบยังไม่พร้อมใช้งาน"); }
}
async function refreshAll() { setAgnes("checking", "กำลังตรวจ Runtime · Provider · Credential Broker · Evidence"); await loadPublicStatus(); await loadProtected(); }

el.composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = el.prompt.value.trim(); const agentId = el.agentSelect.value; if (!prompt || !agentId) return;
  appendMessage("user", prompt); el.send.disabled = true; el.send.textContent = "RUNNING…"; setAgnes("executing", "กำลังส่งงานเข้าสู่ CK-NEXUS execution runtime");
  const payload = { agent_id:agentId, prompt, audience:"ผู้ใช้ CK-NEXUS", platform:"ไม่ระบุ", tone:"เป็นธรรมชาติ", language:"ไทย", session_id:SESSION_ID };
  try {
    const run = await api("/api/runs", {method:"POST",headers:headers(true),body:JSON.stringify(payload)});
    appendMessage("assistant", run.content, `${safe(run.agent_name)} · ${safe(run.mode)} · ${safe(run.duration_ms)} ms`);
    el.prompt.value=""; el.charCount.textContent="0 / 8,000"; setAgnes("ready","งานเสร็จสิ้นและบันทึก run แล้ว");
    const runs = await api(`/api/runs?${new URLSearchParams({session_id:SESSION_ID,limit:"20"})}`, {headers:headers()}); renderRuns(runs);
  } catch (error) { authError(error); setAgnes("warning", `Execution ไม่สำเร็จ · ${error.message}`); }
  finally { el.send.disabled=false; el.send.textContent="SEND ↗"; }
});

el.prompt.addEventListener("input", () => { el.charCount.textContent = `${el.prompt.value.length.toLocaleString()} / 8,000`; el.prompt.style.height="auto"; el.prompt.style.height=`${Math.min(140,el.prompt.scrollHeight)}px`; });
el.sidebarToggle.addEventListener("click", () => el.sidebar.classList.toggle("open"));
el.refresh.addEventListener("click", refreshAll); el.providerRefresh.addEventListener("click", loadProtected);
el.newChat.addEventListener("click", () => { el.prompt.value=""; el.prompt.focus(); if(innerWidth<761) el.sidebar.classList.remove("open"); });
el.accessForm.addEventListener("submit", async (event) => { event.preventDefault(); const token=el.accessToken.value.trim(); if(!token)return; setToken(token); el.dialog.close(); el.accessToken.value=""; await loadProtected(); });
window.addEventListener("keydown", (event) => { if ((event.key === "r" || event.key === "R") && !event.ctrlKey && !event.metaKey && document.activeElement !== el.prompt) refreshAll(); if (event.key === "Escape") el.sidebar.classList.remove("open"); });

refreshAll();