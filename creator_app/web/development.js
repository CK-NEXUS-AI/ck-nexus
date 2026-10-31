(() => {
  "use strict";
  const root = document.getElementById("live-status");
  const banner = document.getElementById("freshness-banner");
  const refreshed = document.getElementById("refreshed-at");
  const authForm = document.getElementById("auth-form");
  const tokenInput = document.getElementById("access-token");
  let accessToken = "";
  if (!root || !banner || !authForm || !tokenInput) return;
  const labels = {
    git: "Git repository", open_prs: "Open pull requests", open_issues: "Open issues",
    main_ci: "Latest main CI", services: "System services", mcp: "MCP listener",
    disk: "Disk usage", production_status: "Production status (RELEASE_STATUS.md only)",
    qwen_probe: "Model Studio / Qwen daily probe"
  };
  function safe(value) {
    if (value === null || value === undefined) return "ตรวจไม่ได้";
    if (typeof value === "string") return value;
    return JSON.stringify(value, null, 2);
  }
  function render(payload) {
    if (!payload || payload.stale || !payload.available) {
      banner.hidden = false;
      banner.textContent = "ข้อมูลเก่า/ตรวจไม่ได้ — ซ่อนค่าก่อนหน้าเพื่อป้องกันการแสดงสถานะค้าง";
      root.replaceChildren();
      refreshed.textContent = "ไม่มีข้อมูลสด";
      return;
    }
    banner.hidden = true;
    const minutes = Math.floor((payload.age_seconds || 0) / 60);
    const sha = payload.items?.git?.status === "ok" ? payload.items.git.value.head : "ตรวจไม่ได้";
    refreshed.textContent = "อัปเดตเมื่อ " + minutes + " นาทีที่แล้ว · commit " + sha;
    root.replaceChildren();
    for (const [key, label] of Object.entries(labels)) {
      const entry = payload.items?.[key];
      const card = document.createElement("article");
      card.className = "stream";
      const title = document.createElement("strong");
      title.textContent = label;
      const status = document.createElement("span");
      status.className = entry?.status === "ok" ? "tool-status good" : "tool-status pending";
      status.textContent = entry?.status === "ok" ? "OK" : "ตรวจไม่ได้";
      const value = document.createElement("pre");
      value.textContent = entry?.status === "ok" ? safe(entry.value) : "ตรวจไม่ได้";
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = "แหล่งข้อมูลและเวลาเก็บ";
      const metadata = document.createElement("pre");
      metadata.textContent = "source: " + (entry?.source || "unknown") +
        "\ncollected_at: " + (entry?.collected_at || "unknown") +
        "\nstatus: " + (entry?.status || "error");
      details.append(summary, metadata);
      card.append(title, status, value, details);
      root.append(card);
    }
  }
  async function refresh() {
    try {
      const response = await fetch("/api/dev-status", {cache: "no-store",
        headers: {
          "Accept": "application/json",
          ...(accessToken ? {"Authorization": "Bearer " + accessToken} : {})
        }});
      if (response.status === 401) {
        accessToken = "";
        render({available: false, stale: true});
        banner.textContent = "ต้องกรอก Access Token เพื่อดูข้อมูลสด";
        return;
      }
      if (!response.ok) throw new Error("HTTP " + response.status);
      render(await response.json());
    } catch (_) {
      render({available: false, stale: true});
    }
  }
  authForm.addEventListener("submit", (event) => {
    event.preventDefault();
    accessToken = tokenInput.value.trim();
    tokenInput.value = "";
    refresh();
  });
  render({available: false, stale: true});
  banner.textContent = "กรอก Access Token เพื่อโหลดข้อมูลสด";
  window.setInterval(refresh, 30000);
})();
