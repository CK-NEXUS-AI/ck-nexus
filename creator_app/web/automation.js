(() => {
  const $ = (id) => document.getElementById(id);
  const labels = {ok:'ผ่าน', blocked:'ต้องยืนยันสิทธิ์', failed:'ผิดพลาด', pending:'ยังไม่ได้ตรวจสอบ', degraded:'ทำงานบางส่วน'};
  const make = (tag, cls, value) => { const el = document.createElement(tag); if (cls) el.className = cls; if (value !== undefined) el.textContent = String(value); return el; };
  const card = (title, state, detail) => { const el = make('article','card'); el.append(make('span',`state ${state}`,labels[state] || labels.pending),make('h3','',title),make('p','',detail)); return el; };
  async function getJson(path) {
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 6500);
    try {
      const headers = {Accept:'application/json'}; const token = $('access-token').value.trim(); if (token) headers.Authorization = `Bearer ${token}`;
      const response = await fetch(path,{method:'GET',headers,credentials:'same-origin',cache:'no-store',signal:controller.signal});
      let data = {}; try { data = await response.json(); } catch (_) { data = {}; }
      if (!response.ok) { const e = new Error(response.status === 401 || response.status === 403 ? 'ปลายทางต้องใช้สิทธิ์เข้าถึงที่ถูกต้อง' : `HTTP ${response.status}`); e.status = response.status; throw e; }
      return data;
    } finally { clearTimeout(timer); }
  }
  const describeError = e => e?.name === 'AbortError' ? 'หมดเวลารอคำตอบ' : (e?.message || 'ตรวจสอบไม่สำเร็จ');
  async function refresh() {
    const button = $('refresh-all'); button.disabled = true; $('last-checked').textContent = 'กำลังตรวจสอบ...';
    $('system-cards').replaceChildren(make('p','muted','กำลังตรวจสอบสถานะจาก API...'));
    $('connection-cards').replaceChildren(make('p','muted','กำลังตรวจสอบ...'));
    $('n8n-panel').replaceChildren(make('p','muted','กำลังโหลดข้อมูล n8n...'));
    const [statusResult, n8nResult] = await Promise.allSettled([getJson('/api/automation/status'),getJson('/api/automation/n8n')]);
    const systems = $('system-cards'); systems.replaceChildren();
    if (statusResult.status === 'fulfilled') {
      const d = statusResult.value;
      (Array.isArray(d.services) ? d.services : []).forEach(s => systems.append(card(s.name || s.id || 'Service',s.state || 'pending',s.message || 'API ไม่ได้ให้รายละเอียด')));
      if (!d.services?.length) systems.append(card('System Status','degraded','API ตอบกลับ แต่ไม่พบข้อมูลบริการในรูปแบบที่คาดไว้'));
      const conns = $('connection-cards'); conns.replaceChildren();
      (Array.isArray(d.integrations) ? d.integrations : []).forEach(i => conns.append(card(i.name || i.id || 'Integration',i.state || 'pending',i.message || 'ยังไม่มีหลักฐานการเชื่อมต่อ')));
      if (!d.integrations?.length) conns.append(card('Integrations','pending','ยังไม่มี API ที่ยืนยันสถานะการเชื่อมต่อ'));
      $('connect-gmail').disabled = !d.gmail_oauth_available;
      $('gmail-action-status').textContent = d.gmail_oauth_available ? 'OAuth API พร้อมให้เริ่มขั้นตอน โดยต้องยืนยันสิทธิ์ตามระบบ' : 'BLOCKED: บริการนี้ยังไม่มี Gmail OAuth API ที่ใช้งานได้';
    } else {
      systems.append(card('Automation Status API',statusResult.reason?.status === 401 ? 'blocked' : 'failed',describeError(statusResult.reason)));
      $('connection-cards').replaceChildren(card('การเชื่อมต่อ','pending','ยังไม่ได้ตรวจสอบ เนื่องจาก Status API ไม่ตอบกลับ'));
      $('connect-gmail').disabled = true; $('gmail-action-status').textContent = 'ยังไม่พร้อม: ต้องตรวจสอบ API ก่อน';
    }
    const panel = $('n8n-panel'); panel.replaceChildren();
    if (n8nResult.status === 'fulfilled' && n8nResult.value.ok) {
      const d = n8nResult.value; const workflows = Array.isArray(d.workflows) ? d.workflows : [];
      const total = Number(d.count ?? workflows.length); const active = Number(d.active ?? workflows.filter(w => w.active).length);
      panel.append(card('n8n Workflows','ok',`ทั้งหมด ${total} · เปิดใช้งาน ${active} · ปิดใช้งาน ${Math.max(0,total-active)}`));
      panel.append(make('p','muted',`ข้อมูลจาก read-only gateway · ตรวจสอบ ${new Date().toLocaleString()}`));
    } else panel.append(card('n8n Gateway',n8nResult.reason?.status === 401 ? 'blocked' : 'failed',n8nResult.status === 'rejected' ? describeError(n8nResult.reason) : (n8nResult.value?.error || 'API ไม่ยืนยันสถานะ')));
    $('last-checked').textContent = `ตรวจสอบเมื่อ ${new Date().toLocaleTimeString()}`; button.disabled = false;
  }
  $('refresh-all').addEventListener('click',() => refresh().catch(e => { $('last-checked').textContent = describeError(e); $('refresh-all').disabled = false; }));
  $('clear-token').addEventListener('click',() => { $('access-token').value = ''; $('gmail-action-status').textContent = 'ล้าง Token จากหน่วยความจำของหน้านี้แล้ว'; });
  $('connect-gmail').addEventListener('click',async () => {
    const button = $('connect-gmail'); button.disabled = true; $('gmail-action-status').textContent = 'กำลังขอลิงก์ OAuth...';
    try { const result = await getJson('/api/integrations/gmail/oauth/start'); if (!result.authorization_url) throw new Error('API ไม่ได้ส่ง authorization URL'); window.location.assign(result.authorization_url); }
    catch (e) { $('gmail-action-status').textContent = `เริ่ม OAuth ไม่สำเร็จ: ${describeError(e)}`; button.disabled = false; }
  });
  let draft = null;
  $('draft-workflow').addEventListener('click',() => {
    const request = $('workflow-request').value.trim(); if (!request) { $('builder-status').textContent = 'กรุณาระบุงานที่ต้องการก่อนสร้างร่าง'; return; }
    draft = {name:'CK-NEXUS Draft - Review Required',nodes:[{parameters:{content:`คำสั่งต้นฉบับ: ${request}\n\nเพิ่ม trigger, processing nodes และ credentials ใน n8n ก่อนใช้งาน`},type:'n8n-nodes-base.stickyNote',typeVersion:1,position:[240,240],id:'cknexus-review-note',name:'Review requirements'}],connections:{},active:false,settings:{executionOrder:'v1'},meta:{ckNexusDraft:true,reviewRequired:true,generatedAt:new Date().toISOString(),source:'CK-NEXUS Automation Control Center'}};
    $('workflow-json').textContent = JSON.stringify(draft,null,2); $('download-workflow').disabled = false; $('builder-status').textContent = 'สร้างร่างแล้ว: เป็นเพียงโน้ตข้อกำหนด ยังไม่มี trigger หรือการเชื่อมต่อจริง ต้องตรวจสอบและแก้ไขใน n8n ก่อนนำไปใช้';
  });
  $('download-workflow').addEventListener('click',() => { if (!draft) return; const url = URL.createObjectURL(new Blob([JSON.stringify(draft,null,2)],{type:'application/json'})); const link = make('a'); link.href = url; link.download = 'ck-nexus-workflow-draft.json'; document.body.append(link); link.click(); link.remove(); URL.revokeObjectURL(url); });
  refresh().catch(e => { $('last-checked').textContent = describeError(e); $('refresh-all').disabled = false; });
})();
