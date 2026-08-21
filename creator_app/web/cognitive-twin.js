(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const root = document.documentElement;
  const body = document.body;
  const accessDialog = $("access-dialog");
  const accessForm = $("access-form");
  const accessTokenInput = $("access-token");
  const accessError = $("access-error");
  const settingsDrawer = $("settings-drawer");
  const inspectorEmpty = $("inspector-empty");
  const inspectorContent = $("inspector-content");
  const scene = $("scene");

  const visualVocabulary = {
    searching: ["◎", "ค้นหา"],
    analyzing: ["◌", "วิเคราะห์"],
    planning: ["⌘", "วางแผน"],
    executing: ["⌬", "ดำเนินงาน"],
    verifying: ["✓", "ตรวจสอบ"],
    waiting: ["…", "รอข้อมูล"],
    blocked: ["×", "ถูกบล็อก"],
    evidence: ["◇", "บันทึกหลักฐาน"],
  };

  const agentCatalog = {
    agnes: {
      name: "AGNES",
      role: "Cognitive Coordinator",
      state: "กำลังประสานข้อมูล",
      truth: "OBSERVED",
      source: "/api/agnes/status",
      task: "สรุปสถานะระบบและเลือก capability ที่เหมาะสม",
      sequence: ["searching", "analyzing", "planning", "verifying"],
    },
    strategos: {
      name: "STRATEGOS",
      role: "Planner / Strategy",
      state: "พร้อมวางแผน",
      truth: "INFERRED",
      source: "Role projection",
      task: "ยังไม่มี task ที่ยืนยันได้",
      sequence: ["analyzing", "planning", "waiting"],
    },
    scout: {
      name: "SCOUT",
      role: "Research / Discovery",
      state: "เฝ้าดูแหล่งข้อมูล",
      truth: "INFERRED",
      source: "Role projection",
      task: "ยังไม่มี task ที่ยืนยันได้",
      sequence: ["searching", "analyzing", "evidence"],
    },
    verifier: {
      name: "VERIFIER",
      role: "Independent Verification",
      state: "รอหลักฐาน",
      truth: "INFERRED",
      source: "Role projection",
      task: "ยังไม่มี task ที่ยืนยันได้",
      sequence: ["waiting", "verifying", "evidence"],
    },
    guardian: {
      name: "GUARDIAN",
      role: "Security / Policy",
      state: "เฝ้าระบบ",
      truth: "INFERRED",
      source: "Role projection",
      task: "ตรวจนโยบาย สิทธิ์ และสถานะความเสี่ยง",
      sequence: ["analyzing", "verifying", "blocked"],
    },
    builder: {
      name: "BUILDER",
      role: "Automation Builder",
      state: "พร้อมทำงาน",
      truth: "INFERRED",
      source: "Role projection",
      task: "ยังไม่มี task ที่ยืนยันได้",
      sequence: ["planning", "executing", "verifying"],
    },
  };

  let accessToken = sessionStorage.getItem("cknexus_access_token") || "";
  let selectedAgent = null;
  let pollHandle = null;
  let semanticMotion = true;
  let microMotion = true;
  let backgroundPause = true;

  function headers() {
    return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
  }

  async function getJson(path) {
    const response = await fetch(path, { headers: headers(), cache: "no-store" });
    if (!response.ok) {
      const error = new Error(`${response.status} ${response.statusText}`);
      error.status = response.status;
      throw error;
    }
    return response.json();
  }

  function setText(id, value) {
    const node = $(id);
    if (node) node.textContent = value ?? "—";
  }

  function boolText(value) {
    if (value === true) return "เปิด";
    if (value === false) return "ปิด";
    return value ?? "—";
  }

  function safeLedgerStatus(ledger) {
    if (!ledger || typeof ledger !== "object") return "—";
    if ("valid" in ledger) return ledger.valid ? "VALID" : "INVALID";
    if ("ok" in ledger) return ledger.ok ? "VALID" : "INVALID";
    if ("result" in ledger) return String(ledger.result);
    return "AVAILABLE";
  }

  function safeKernelState(kernel) {
    if (!kernel || typeof kernel !== "object") return "UNKNOWN";
    return String(kernel.state || kernel.status || kernel.mode || "AVAILABLE").toUpperCase();
  }

  function inferAgnesVisualState(data) {
    const inference = data?.inference || {};
    const kernel = data?.execution_kernel || {};
    if (!inference.ready) return { key: "waiting", label: "รอ inference runtime", live: "blocked" };
    const state = String(kernel.state || kernel.status || "").toLowerCase();
    if (state.includes("verify")) return { key: "verifying", label: "กำลังตรวจสอบ", live: "verify" };
    if (state.includes("run") || state.includes("execut")) return { key: "executing", label: "กำลังดำเนินงาน", live: "busy" };
    return { key: "analyzing", label: "พร้อมประสานงาน", live: "busy" };
  }

  function applyAgnesRuntime(data) {
    const visual = inferAgnesVisualState(data);
    setText("top-agnes", visual.label);
    setText("state-agnes", visual.label);
    setText("agnes-mode", data?.inference?.mode || "UNKNOWN");
    setText("agnes-agent", data?.agent || "AGNES");
    setText("agnes-skills", data?.skill_count ?? "—");
    setText("agnes-inference", data?.inference?.provider || data?.inference?.mode || "—");
    setText("agnes-ledger", safeLedgerStatus(data?.ledger));
    setText("kernel-state", safeKernelState(data?.execution_kernel));
    setText("kernel-dispatcher", data?.execution_kernel?.dispatcher || data?.execution_kernel?.mode || "AVAILABLE");
    setText("kernel-sandbox", boolText(data?.execution_kernel?.sandbox_enabled));
    setText("kernel-pipeline", boolText(data?.autonomous_dev_pipeline?.enabled));
    setText("kernel-policy", data?.policy?.allow_production_mutation ? "MUTATION ENABLED" : "FAIL-CLOSED");

    const agentNode = document.querySelector('[data-agent="agnes"]');
    if (agentNode) agentNode.dataset.live = visual.live;
    setText("symbol-agnes", visualVocabulary[visual.key]?.[0] || "◌");
    agentCatalog.agnes.state = visual.label;
    agentCatalog.agnes.task = data?.autonomous_dev_pipeline?.enabled
      ? "ติดตาม execution pipeline และประสาน verification"
      : "ติดตาม runtime, skills, policy และ evidence state";
    agentCatalog.agnes.sequence = visual.key === "waiting"
      ? ["waiting", "verifying"]
      : ["searching", "analyzing", visual.key, "verifying"];
    if (selectedAgent === "agnes") renderInspector("agnes");
  }

  function applyProviderRuntime(data) {
    const providers = Array.isArray(data?.providers) ? data.providers : [];
    const available = providers.filter((item) => item.available && !item.circuit_open);
    setText("top-provider", data?.preferred || "ไม่มี preferred");
    setText("provider-state", available.length ? "AVAILABLE" : "UNAVAILABLE");
    setText("provider-preferred", data?.preferred || "—");
    setText("provider-local", boolText(data?.policy?.local_first));
    setText("provider-cloud", boolText(data?.policy?.allow_cloud));
    setText("provider-count", `${available.length}/${providers.length}`);
  }

  function applyExecutionRuntime(data) {
    if (!data || typeof data !== "object") return;
    setText("kernel-state", safeKernelState(data));
    setText("kernel-dispatcher", data.dispatcher || data.mode || "AVAILABLE");
    setText("kernel-sandbox", boolText(data.sandbox_enabled));
  }

  function setConnection(ok, label) {
    const pill = $("connection-pill");
    pill.classList.toggle("connected", ok);
    pill.querySelector("span").textContent = label;
    setText("top-system", ok ? "เชื่อมต่อแล้ว" : "เชื่อมต่อไม่สำเร็จ");
    $("top-system").classList.toggle("good", ok);
    $("top-system").classList.toggle("danger", !ok);
  }

  async function refreshRuntime({ showAuth = true } = {}) {
    try {
      const [agnes, execution, providers] = await Promise.all([
        getJson("/api/agnes/status"),
        getJson("/api/agnes/execution/status"),
        getJson("/api/providers/status"),
      ]);
      applyAgnesRuntime(agnes);
      applyExecutionRuntime(execution);
      applyProviderRuntime(providers);
      setConnection(true, "LIVE / REAL API");
      accessDialog.classList.add("hidden");
      accessError.textContent = "";
      return true;
    } catch (error) {
      setConnection(false, error.status === 401 ? "ต้องยืนยันสิทธิ์" : "API ไม่พร้อม");
      if (error.status === 401 && showAuth) accessDialog.classList.remove("hidden");
      if (error.status !== 401) accessDialog.classList.add("hidden");
      return false;
    }
  }

  function schedulePolling() {
    if (pollHandle) window.clearInterval(pollHandle);
    pollHandle = window.setInterval(() => {
      if (document.hidden && backgroundPause) return;
      refreshRuntime({ showAuth: false });
      moveAmbientAgents();
    }, 5000);
  }

  function visualSentence(sequence) {
    return sequence.map((key, index) => {
      const [icon, label] = visualVocabulary[key] || ["·", key];
      const arrow = index ? '<span class="arrow">→</span>' : "";
      return `${arrow}<span class="visual-token"><i>${icon}</i><b>${label}</b></span>`;
    }).join("");
  }

  function renderInspector(agentId) {
    const item = agentCatalog[agentId];
    if (!item) return;
    selectedAgent = agentId;
    inspectorEmpty.classList.add("hidden");
    inspectorContent.classList.remove("hidden");
    setText("inspector-name", item.name);
    setText("inspector-role", item.role);
    setText("inspector-state", item.state);
    setText("inspector-task", item.task);
    setText("inspector-source", item.source);
    setText("inspector-truth", item.truth);
    $("visual-sentence").innerHTML = visualSentence(item.sequence);
    $("inspector-portrait").className = `portrait portrait-${agentId}`;
  }

  function closeInspector() {
    selectedAgent = null;
    inspectorContent.classList.add("hidden");
    inspectorEmpty.classList.remove("hidden");
  }

  function moveAmbientAgents() {
    if (!semanticMotion || root.dataset.motion === "reduced") return;
    document.querySelectorAll(".agent").forEach((node, index) => {
      if (node.dataset.agent === "agnes") return;
      const x = ((Date.now() / 1000 + index * 11) % 13) - 6;
      const y = Math.sin(Date.now() / 4500 + index) * 2;
      node.style.translate = `${x}px ${y}px`;
    });
  }

  function loadSettings() {
    try {
      const saved = JSON.parse(localStorage.getItem("cknexus_twin_settings") || "{}");
      if (saved.fontScale) $("font-scale").value = saved.fontScale;
      if (saved.motionQuality) $("motion-quality").value = saved.motionQuality;
      if (saved.lodMode) $("lod-mode").value = saved.lodMode;
      $("high-contrast").checked = Boolean(saved.highContrast);
      $("semantic-motion").checked = saved.semanticMotion !== false;
      $("micro-motion").checked = saved.microMotion !== false;
      $("particles").checked = saved.particles !== false;
      $("background-pause").checked = saved.backgroundPause !== false;
      $("show-inferred").checked = saved.showInferred !== false;
      $("show-simulated").checked = Boolean(saved.showSimulated);
    } catch (_) {
      // Ignore malformed local preference data and fall back to safe defaults.
    }
    applySettings();
  }

  function applySettings() {
    const fontScale = Number($("font-scale").value || 100) / 100;
    root.style.setProperty("--font-scale", fontScale.toFixed(2));
    root.dataset.motion = $("motion-quality").value;
    semanticMotion = $("semantic-motion").checked;
    microMotion = $("micro-motion").checked;
    backgroundPause = $("background-pause").checked;
    body.classList.toggle("high-contrast", $("high-contrast").checked);
    body.classList.toggle("no-micro-motion", !microMotion);
    body.classList.toggle("no-particles", !$("particles").checked);
    body.classList.toggle("hide-inferred", !$("show-inferred").checked);
    body.classList.toggle("show-simulated", $("show-simulated").checked);
    const settings = {
      fontScale: $("font-scale").value,
      motionQuality: $("motion-quality").value,
      lodMode: $("lod-mode").value,
      highContrast: $("high-contrast").checked,
      semanticMotion,
      microMotion,
      particles: $("particles").checked,
      backgroundPause,
      showInferred: $("show-inferred").checked,
      showSimulated: $("show-simulated").checked,
    };
    localStorage.setItem("cknexus_twin_settings", JSON.stringify(settings));
  }

  document.querySelectorAll(".agent").forEach((node) => {
    node.addEventListener("click", () => renderInspector(node.dataset.agent));
  });

  document.querySelectorAll(".nav-item").forEach((node) => {
    node.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
      node.classList.add("active");
      const view = node.dataset.view;
      setText("holo-title", `${String(view).toUpperCase()} / LIVE VIEW`);
      scene.dataset.view = view;
    });
  });

  document.querySelectorAll("[data-camera]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-camera]").forEach((item) => item.classList.remove("selected"));
      button.classList.add("selected");
      scene.dataset.camera = button.dataset.camera;
    });
  });

  document.querySelectorAll("[data-agent-action]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!selectedAgent) return;
      const action = button.dataset.agentAction;
      if (action === "follow") scene.dataset.camera = "agent";
      if (action === "focus") body.classList.add("focus-mode");
      if (action === "evidence") {
        setText("inspector-task", `${agentCatalog[selectedAgent].task} / Evidence view is read-only`);
      }
    });
  });

  $("close-inspector").addEventListener("click", closeInspector);
  $("open-settings").addEventListener("click", () => settingsDrawer.classList.remove("hidden"));
  $("close-settings").addEventListener("click", () => settingsDrawer.classList.add("hidden"));
  $("toggle-focus").addEventListener("click", () => body.classList.toggle("focus-mode"));

  ["font-scale", "motion-quality", "lod-mode", "high-contrast", "semantic-motion", "micro-motion", "particles", "background-pause", "show-inferred", "show-simulated"].forEach((id) => {
    $(id).addEventListener("input", applySettings);
    $(id).addEventListener("change", applySettings);
  });

  accessForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    accessToken = accessTokenInput.value.trim();
    if (accessToken) sessionStorage.setItem("cknexus_access_token", accessToken);
    else sessionStorage.removeItem("cknexus_access_token");
    accessError.textContent = "กำลังตรวจสอบสิทธิ์...";
    const ok = await refreshRuntime({ showAuth: true });
    accessError.textContent = ok ? "" : "ไม่สามารถยืนยันสิทธิ์หรือ runtime ยังไม่พร้อม";
  });

  $("continue-without-token").addEventListener("click", async () => {
    accessToken = "";
    sessionStorage.removeItem("cknexus_access_token");
    const ok = await refreshRuntime({ showAuth: false });
    if (!ok) accessError.textContent = "Runtime นี้ต้องใช้ Access Token";
  });

  $("connection-pill").addEventListener("click", () => refreshRuntime({ showAuth: true }));

  document.addEventListener("visibilitychange", () => {
    body.classList.toggle("paused", document.hidden && backgroundPause);
  });

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reduceMotion.matches) {
    $("motion-quality").value = "reduced";
  }

  loadSettings();
  schedulePolling();
  if (accessToken) {
    refreshRuntime({ showAuth: true });
  } else {
    refreshRuntime({ showAuth: false }).then((ok) => {
      if (!ok) accessDialog.classList.remove("hidden");
    });
  }
})();
