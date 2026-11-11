(() => {
  const form = document.querySelector("#intent-form");
  const goal = document.querySelector("#intent-goal");
  const button = document.querySelector("#plan-button");
  const status = document.querySelector("#intent-status");
  const panel = document.querySelector("#plan-panel");
  const skillsNode = document.querySelector("#plan-skills");
  const actions = document.querySelector("#context-actions");
  if (!form || !goal || !button || !panel || !skillsNode) return;

  const elements = {
    summary: document.querySelector("#plan-summary"), state: document.querySelector("#plan-state"),
    permissions: document.querySelector("#permission-preview"), evidencePlan: document.querySelector("#evidence-plan"),
  };
  const agentHints = [
    { terms: ["คอนเทนต์", "สคริปต์", "วิดีโอ", "บทความ", "โพสต์", "content", "script"], id: "content" },
    { terms: ["ค้นคว้า", "วิจัย", "สรุป", "แหล่งที่มา", "research", "summar"], id: "research" },
    { terms: ["โค้ด", "code", "repository", "repo", "ทดสอบ", "test"], id: "code" },
    { terms: ["เว็บไซต์", "เว็บ", "design", "ออกแบบ", "ลูกค้า", "crm"], id: "connected-tool" },
  ];

  const node = (tag, text, className) => {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = String(text);
    if (className) item.className = className;
    return item;
  };

  function contextualHint(text) {
    const normalized = text.toLowerCase();
    const match = agentHints.find((item) => item.terms.some((term) => normalized.includes(term)));
    if (!match) return "แสดงทักษะที่ตรงกับคำขอจาก catalog เท่านั้น";
    if (match.id === "content") return "พบคำขอด้านคอนเทนต์ · Creator Workspace รองรับการสร้างร่างข้อความ";
    if (match.id === "research") return "พบคำขอด้านค้นคว้า · ตรวจสอบทักษะและสถานะผู้ให้บริการก่อนใช้งานจริง";
    if (match.id === "code") return "พบคำขอด้านโค้ด · แผนไม่แก้ไฟล์หรือรันทดสอบแทนผู้ใช้";
    return "อาจเกี่ยวข้องกับเครื่องมือภายนอก · แสดงเฉพาะ connector ที่ตรวจพบจาก runtime";
  }

  function renderSkills(plan) {
    skillsNode.replaceChildren();
    const skills = Array.isArray(plan.skills) ? plan.skills : [];
    if (!skills.length) {
      skillsNode.append(node("p", "ไม่พบ Skill ที่ตรงกับเป้าหมาย", "muted"));
      return;
    }
    skills.forEach((skill) => {
      const card = node("article", undefined, "skill-item");
      card.append(node("strong", skill.id || "Unnamed capability"));
      card.append(node("small", `${skill.organ || "ไม่ระบุหมวด"} · ${skill.description || "ไม่มีคำอธิบาย"}`));
      const tags = node("div", undefined, "skill-tags");
      [skill.risk || "risk_unknown", skill.executor || "executor_unknown", ...(skill.approval_required ? ["ต้องอนุมัติ"] : [])].forEach((value) => tags.append(node("span", value)));
      card.append(tags);
      skillsNode.append(card);
    });
  }

  function renderPermissions(plan) {
    const skills = Array.isArray(plan.skills) ? plan.skills : [];
    const capabilities = [...new Set(skills.flatMap((skill) => Array.isArray(skill.capabilities) ? skill.capabilities : []))];
    const risks = [...new Set(skills.map((skill) => skill.risk || "unknown"))];
    const approval = plan.requires_approval ? "แผนระบุว่าต้องมีการอนุมัติ · ยังไม่มีการอนุมัติ" : "ไม่พบข้อกำหนดอนุมัติในแผนนี้ · ไม่ใช่สิทธิ์ให้ดำเนินการ";
    const rows = [
      ["ข้อมูลที่จะเข้าถึง", "เป้าหมายที่พิมพ์และ metadata ของ Skill Catalog เท่านั้น"],
      ["ความสามารถที่ระบุ", capabilities.length ? capabilities.join(", ") : "ไม่มี capability ระบุไว้"],
      ["ความเสี่ยงที่ระบุ", risks.length ? risks.join(", ") : "ยังไม่ประเมิน"],
      ["ขอบเขตเปลี่ยนแปลง", "ไม่มี · Dry Run ไม่เรียก executor หรือเปลี่ยนข้อมูล"],
      ["การอนุมัติ", approval],
    ];
    elements.permissions.replaceChildren();
    rows.forEach(([label, value]) => {
      const row = node("div");
      row.append(node("dt", label), node("dd", value));
      elements.permissions.append(row);
    });
  }

  function suggestCreator(text) {
    const relevant = agentHints[0].terms.some((term) => text.toLowerCase().includes(term));
    actions.hidden = !relevant;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const objective = goal.value.trim();
    if (!objective) { goal.focus(); return; }
    button.disabled = true;
    button.firstElementChild.textContent = "กำลังสร้างแผน…";
    status.textContent = "กำลังเรียก Agnes Plan API · ยังไม่มีการดำเนินการจริง";
    panel.hidden = false;
    elements.state.textContent = "กำลังวางแผน";
    elements.summary.textContent = contextualHint(objective);
    skillsNode.replaceChildren(node("p", "กำลังอ่าน Skill Catalog…", "muted"));
    try {
      const params = new URLSearchParams({ goal: objective });
      const tokenInput = document.querySelector("#access-token");
      const token = tokenInput?.value.trim() || sessionStorage.getItem("cknexus_access_token") || "";
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const response = await fetch(`/api/agnes/plan?${params}`, { headers });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = payload.detail || payload;
        throw new Error(detail.message || detail.error || `HTTP ${response.status}`);
      }
      renderSkills(payload);
      renderPermissions(payload);
      elements.state.textContent = payload.requires_approval ? "รออนุมัติก่อน execution" : "Dry Run · ไม่ได้ดำเนินการ";
      elements.summary.textContent = `${contextualHint(objective)} · Plan ID: ${payload.plan_id || "ไม่ระบุ"}`;
      elements.evidencePlan.textContent = `สร้างแล้ว · ${payload.plan_id || "plan"}`;
      status.textContent = "สร้างแผนสำเร็จ · ยังไม่มีการเรียกใช้เครื่องมือหรือเปลี่ยนข้อมูลจริง";
      suggestCreator(objective);
      panel.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    } catch (error) {
      elements.state.textContent = "สร้างแผนไม่สำเร็จ";
      elements.summary.textContent = "ไม่สามารถอ่านแผนจาก Agnes ได้ จึงไม่แสดงการอนุญาตหรือความสามารถที่คาดเดาเอง";
      skillsNode.replaceChildren(node("p", error.message, "muted"));
      status.textContent = "ไม่สามารถสร้างแผนได้ · ไม่มีการดำเนินการ";
      actions.hidden = true;
    } finally {
      button.disabled = false;
      button.firstElementChild.textContent = "สร้างแผนให้ตรวจสอบ";
    }
  });

  document.querySelectorAll("[data-intent]").forEach((chip) => chip.addEventListener("click", () => {
    goal.value = chip.dataset.intent || "";
    goal.focus();
  }));
  document.querySelector("#open-creator")?.addEventListener("click", () => {
    const disclosure = document.querySelector("#creator-disclosure");
    disclosure.open = true;
    const prompt = document.querySelector("#prompt");
    prompt.value = goal.value;
    document.querySelector("#char-count").textContent = String(prompt.value.length);
    prompt.focus();
    disclosure.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  });
})();
