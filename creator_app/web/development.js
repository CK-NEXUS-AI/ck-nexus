(() => {
  "use strict";
  const root = document.getElementById("live-status");
  const banner = document.getElementById("freshness-banner");
  const refreshed = document.getElementById("refreshed-at");
  const authForm = document.getElementById("auth-form");
  const tokenInput = document.getElementById("access-token");
  if (!root || !banner || !authForm || !tokenInput) return;

  let accessToken = "";
  const labels = {
    git: "Git repository",
    open_prs: "Open pull requests",
    open_issues: "Open issues",
    main_ci: "Latest main CI",
    services: "System services",
    mcp: "MCP listener",
    disk: "Disk usage",
    production_status: "Production status (release status source)",
    qwen_probe: "Model Studio / Qwen probe"
  };

  function text(value) {
    if (value === null || value === undefined || value === "") return "NOT_VERIFIED";
    return typeof value === "string" ? value : JSON.stringify(value, null, 2);
  }

  function setText(element, value) {
    element.textContent = text(value);
  }

  function ensureEvidencePanel() {
    let panel = document.getElementById("verified-status-boundary");
    if (panel) return panel;
    panel = document.createElement("section");
    panel.id = "verified-status-boundary";
    panel.className = "panel status-boundary";
    panel.setAttribute("aria-labelledby", "status-boundary-title");
    const title = document.createElement("h2");
    title.id = "status-boundary-title";
    title.textContent = "Verified status boundaries";
    const runtime = document.createElement("p");
    runtime.textContent = "Canonical runtime: python -m creator_app.unified. Runtime health: NOT_VERIFIED (no live health request is performed by this dashboard).";
    const prod = document.createElement("p");
    prod.className = "no-go-status";
    prod.textContent = "Production eligibility: NO-GO. Q10–Q16 are not promoted by dashboard or ordinary CI evidence.";
    const evidence = document.createElement("p");
    evidence.textContent = "CI evidence source: GitHub Actions run 41781983676 (CK-NEXUS CI, main, 2026-11-04); 41781983784 (Trusted Verifier Image CI, main, 2026-11-04); 41781983695 (Code Quality, main, 2026-11-04). These runs do not establish production health or Q10–Q16 completion.";
    panel.append(title, runtime, prod, evidence);
    const form = document.getElementById("auth-form");
    if (form && form.parentNode) form.parentNode.insertBefore(panel, form.nextSibling);
    else document.body.insertBefore(panel, document.body.firstChild);
    return panel;
  }

  function render(payload) {
    ensureEvidencePanel();
    if (!payload || payload.stale || !payload.available) {
      banner.hidden = false;
      banner.textContent = "Status snapshot is unavailable or stale. Previous snapshot values are suppressed; no live status is asserted.";
      root.replaceChildren();
      setText(refreshed, "No current snapshot");
      return;
    }

    banner.hidden = true;
    setText(refreshed, "Snapshot collected at " + (payload.collected_at || "NOT_VERIFIED") +
      " · age_seconds=" + (payload.age_seconds ?? "NOT_VERIFIED"));
    root.replaceChildren();
    for (const [key, label] of Object.entries(labels)) {
      const entry = payload.items && payload.items[key];
      const card = document.createElement("article");
      card.className = "stream";
      const title = document.createElement("strong");
      title.textContent = label;
      const status = document.createElement("span");
      const valid = entry && entry.status === "ok";
      status.className = valid ? "tool-status good" : "tool-status pending";
      status.textContent = valid ? "OBSERVED" : "NOT_VERIFIED";
      const value = document.createElement("pre");
      value.textContent = valid ? text(entry.value) : "No usable evidence in the current snapshot.";
      const metadata = document.createElement("pre");
      metadata.textContent = "source: " + text(entry && entry.source) +
        "\ncollected_at: " + text(entry && entry.collected_at) +
        "\nstatus: " + text(entry && entry.status);
      card.append(title, status, value, metadata);
      root.append(card);
    }
  }

  async function refresh() {
    try {
      const response = await fetch("/api/dev-status", {
        cache: "no-store",
        headers: {
          Accept: "application/json",
          ...(accessToken ? { Authorization: "Bearer " + accessToken } : {})
        }
      });
      if (response.status === 401) {
        accessToken = "";
        render({ available: false, stale: true });
        banner.textContent = "Access token required to read the protected status snapshot.";
        return;
      }
      if (!response.ok) throw new Error("HTTP " + response.status);
      render(await response.json());
    } catch (_) {
      render({ available: false, stale: true });
    }
  }

  authForm.addEventListener("submit", (event) => {
    event.preventDefault();
    accessToken = tokenInput.value.trim();
    tokenInput.value = "";
    refresh();
  });

  ensureEvidencePanel();
  render({ available: false, stale: true });
  banner.textContent = "Enter the CK-NEXUS access token to request a fresh status snapshot.";
  window.setInterval(refresh, 30000);
})();
