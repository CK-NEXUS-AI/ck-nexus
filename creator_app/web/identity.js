(() => {
  const statusNode = document.getElementById("identity-status");
  const profileNode = document.getElementById("identity-profile");
  const connectNode = document.getElementById("github-connect");
  const revokeNode = document.getElementById("github-revoke");
  const resultNode = document.getElementById("identity-result");

  function showStatus(text, state) {
    statusNode.dataset.state = state;
    statusNode.replaceChildren();
    const dot = document.createElement("span");
    dot.className = "status-dot";
    const label = document.createElement("span");
    label.textContent = text;
    statusNode.append(dot, label);
  }

  async function refreshStatus() {
    try {
      const response = await fetch("/api/identity/github/status", {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("status unavailable");
      const data = await response.json();
      if (data.verified && data.identity) {
        showStatus("ยืนยันตัวตนสำเร็จ", "verified");
        document.getElementById("identity-login").textContent = "@" + data.identity.login;
        document.getElementById("identity-user-id").textContent = "GitHub user ID: " + data.identity.user_id;
        const avatar = document.getElementById("identity-avatar");
        if (data.identity.avatar_url) avatar.src = data.identity.avatar_url;
        else avatar.removeAttribute("src");
        profileNode.hidden = false;
        connectNode.hidden = true;
        revokeNode.hidden = false;
      } else if (!data.configured) {
        showStatus("ต้องตั้งค่า GitHub OAuth ก่อนใช้งาน", "error");
        connectNode.setAttribute("aria-disabled", "true");
        connectNode.href = "#configuration-required";
        document.getElementById("identity-note").textContent =
          "ผู้ดูแลต้องตั้งค่า CKNEXUS_GITHUB_OAUTH_CLIENT_ID, CKNEXUS_GITHUB_OAUTH_CLIENT_SECRET และ CKNEXUS_GITHUB_OAUTH_REDIRECT_URI";
      } else {
        showStatus("ยังไม่ได้ยืนยันตัวตน", "idle");
      }
    } catch {
      showStatus("ไม่สามารถตรวจสอบสถานะได้ โปรดลองใหม่", "error");
    }
  }

  const params = new URLSearchParams(window.location.search);
  const result = params.get("result");
  if (result === "cancelled") resultNode.textContent = "คุณยกเลิกการยืนยันตัวตน";
  else if (result === "not-configured") resultNode.textContent = "ยังตั้งค่า GitHub OAuth ไม่ครบ";
  else if (result === "failed") resultNode.textContent = "ยืนยันตัวตนไม่สำเร็จ หรือเซสชันหมดอายุ";

  revokeNode.addEventListener("click", async () => {
    revokeNode.disabled = true;
    try {
      await fetch("/api/identity/github/revoke", {
        method: "POST",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      profileNode.hidden = true;
      connectNode.hidden = false;
      resultNode.textContent = "ยกเลิกเซสชันยืนยันตัวตนแล้ว";
      showStatus("ยังไม่ได้ยืนยันตัวตน", "idle");
    } catch {
      resultNode.textContent = "ยกเลิกเซสชันไม่สำเร็จ";
    } finally {
      revokeNode.disabled = false;
    }
  });

  refreshStatus();
})();
