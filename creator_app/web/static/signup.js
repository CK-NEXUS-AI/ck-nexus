const API = '/api/providers';
let providers = [];
let scanData = [];

async function init() {
  try {
    const r = await fetch(`${API}/list`);
    providers = await r.json();
  } catch { providers = []; }
  renderGrid();
  populateSelect();
  checkSystem();
  autoScan();
}

function checkSystem() {
  fetch('/health').then(r => r.json()).then(() => {
    document.getElementById('sysDot').classList.add('live');
    document.getElementById('sysLabel').textContent = 'LIVE';
  }).catch(() => {
    document.getElementById('sysLabel').textContent = 'OFFLINE';
  });
}

function renderGrid() {
  const g = document.getElementById('providerGrid');
  g.innerHTML = providers.map(p => `
    <div class="provider-card" id="card-${p.slug}">
      <div class="provider-head">
        <span class="provider-icon">${p.icon}</span>
        <div class="provider-info">
          <div class="provider-name">${p.name}</div>
          <span class="provider-tier tier-${p.tier}">${p.tier}</span>
        </div>
      </div>
      <div class="provider-desc">${p.description}</div>
      <div class="provider-models">
        ${(p.free_models||[]).map(m => `<span class="model-chip">${m}</span>`).join('')}
      </div>
      <div class="provider-status">
        <span class="dot" id="dot-${p.slug}"></span>
        <span class="label" id="lbl-${p.slug}">Not scanned</span>
      </div>
      <div class="provider-actions">
        <a href="${p.signup_url}" target="_blank" class="btn-action">🔑 Get Key</a>
        <a href="${p.docs_url}" target="_blank" class="btn-action">📖 Docs</a>
        <button class="btn-action" onclick="validateOne('${p.slug}')">✅ Validate</button>
      </div>
    </div>
  `).join('');
}

function populateSelect() {
  const s = document.getElementById('provSelect');
  providers.forEach(p => {
    const o = document.createElement('option');
    o.value = p.slug;
    o.textContent = `${p.icon} ${p.name}`;
    s.appendChild(o);
  });
}

async function autoScan() {
  try {
    const r = await fetch(`${API}/scan`);
    scanData = await r.json();
    updateCards(scanData);
    updateStats(scanData);
  } catch {}
}

async function runScan() {
  const btn = document.getElementById('scanBtn');
  const st = document.getElementById('scanStatus');
  btn.disabled = true;
  document.getElementById('scanIcon').textContent = '⏳';
  st.textContent = 'Scanning all providers...';
  document.querySelectorAll('.provider-card').forEach(c => c.classList.add('scanning'));

  try {
    const r = await fetch(`${API}/scan`);
    scanData = await r.json();
    updateCards(scanData);
    updateStats(scanData);
    const found = scanData.filter(d => d.has_key).length;
    st.textContent = `✅ Complete — ${found}/${scanData.length} keys detected`;
  } catch { st.textContent = '❌ Backend not connected'; }

  document.querySelectorAll('.provider-card').forEach(c => c.classList.remove('scanning'));
  btn.disabled = false;
  document.getElementById('scanIcon').textContent = '🔍';
}

function updateCards(data) {
  data.forEach(d => {
    const card = document.getElementById(`card-${d.slug}`);
    const dot = document.getElementById(`dot-${d.slug}`);
    const lbl = document.getElementById(`lbl-${d.slug}`);
    if (!card) return;
    card.classList.toggle('active', d.has_key);
    dot.classList.toggle('active', d.has_key);
    lbl.classList.toggle('active', d.has_key);
    lbl.textContent = d.has_key ? `✅ Active (${d.key_preview})` : '❌ No key';
  });
}

function updateStats(data) {
  document.getElementById('statTotal').textContent = data.length;
  document.getElementById('statActive').textContent = data.filter(d => d.has_key).length;
  const models = data.reduce((s, d) => s + (d.free_models||[]).length, 0);
  document.getElementById('statModels').textContent = models;
}

async function validateOne(slug) {
  const lbl = document.getElementById(`lbl-${slug}`);
  const dot = document.getElementById(`dot-${slug}`);
  lbl.textContent = '⏳ Validating...';
  lbl.style.color = 'var(--hub-yellow)';
  try {
    const r = await fetch(`${API}/${slug}/validate`);
    const v = await r.json();
    if (v.valid) {
      lbl.textContent = `✅ Valid (${v.key_preview})`;
      lbl.style.color = 'var(--hub-green)';
      dot.classList.add('active');
      document.getElementById(`card-${slug}`).classList.add('active');
    } else {
      lbl.textContent = `❌ ${v.error}`;
      lbl.style.color = 'var(--hub-red)';
      dot.classList.remove('active');
    }
  } catch { lbl.textContent = '❌ Connection error'; lbl.style.color = 'var(--hub-red)'; }
}

async function addKey() {
  const slug = document.getElementById('provSelect').value;
  const key = document.getElementById('keyInput').value;
  const msg = document.getElementById('formMsg');
  if (!slug || !key) { msg.innerHTML = '<span style="color:var(--hub-red)">⚠️ Select provider and enter key</span>'; return; }
  try {
    const r = await fetch(`${API}/${slug}/set-key`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({key}),
    });
    const d = await r.json();
    if (d.success) {
      msg.innerHTML = `<span style="color:var(--hub-green)">✅ Key set for ${slug}</span>`;
      document.getElementById('keyInput').value = '';
      runScan();
    } else { msg.innerHTML = `<span style="color:var(--hub-red)">❌ ${d.error}</span>`; }
  } catch { msg.innerHTML = '<span style="color:var(--hub-red)">❌ Backend not connected</span>'; }
}

async function validateAll() {
  const panel = document.getElementById('resultsPanel');
  const list = document.getElementById('resultsList');
  panel.style.display = 'block';
  list.innerHTML = '<p style="color:var(--hub-dim)">⏳ Validating...</p>';
  try {
    const r = await fetch(`${API}/validate-all`);
    const results = await r.json();
    list.innerHTML = results.map(r => `
      <div class="result-row">
        <span class="result-icon">${r.icon}</span>
        <span class="result-name">${r.name}</span>
        <span class="result-badge ${r.valid?'badge-ok':'badge-fail'}">${r.valid?'✅ VALID':'❌ '+(r.error||'Invalid')}</span>
      </div>
    `).join('');
  } catch { list.innerHTML = '<p style="color:var(--hub-red)">❌ Backend not connected</p>'; }
}

function exportJSON() {
  const cfg = { version: '1.0', timestamp: new Date().toISOString(), providers: scanData.filter(d=>d.has_key) };
  const b = new Blob([JSON.stringify(cfg,null,2)],{type:'application/json'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(b);
  a.download = `ck-nexus-providers-${Date.now()}.json`; a.click();
}

function genEnv() {
  const panel = document.getElementById('envPanel');
  const pre = document.getElementById('envContent');
  panel.style.display = 'block';
  let env = `# CK-NEXUS Provider Configuration\n# Generated: ${new Date().toISOString()}\n\n`;
  scanData.forEach(d => {
    const p = providers.find(x => x.slug === d.slug);
    env += `# ${d.icon} ${d.name} (${d.has_key?'ACTIVE':'NOT SET'})\n`;
    env += `# ${p?.signup_url||''}\n`;
    env += d.has_key ? `${d.env_key}=${d.key_preview}\n` : `# ${d.env_key}=\n`;
    env += '\n';
  });
  pre.textContent = env;
}

function copyEnv() {
  navigator.clipboard.writeText(document.getElementById('envContent').textContent).then(() => {
    const b = event.target; b.textContent = '✅ Copied!';
    setTimeout(() => b.textContent = '📋 Copy to Clipboard', 2000);
  });
}

init();
