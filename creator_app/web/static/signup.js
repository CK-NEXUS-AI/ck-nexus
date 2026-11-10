const API = '/api/providers';
let providers = [];
let scanData = [];

async function init() {
  try {
    const r = await fetch(`${API}/list`);
    providers = await r.json();
  } catch { providers = []; }
  renderGrid();
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

function safeProviderSlug(value) {
  const slug = String(value || '');
  return /^[a-z0-9_-]+$/i.test(slug) ? slug : '';
}

function safeProviderUrl(value) {
  try {
    const url = new URL(String(value || ''));
    return url.protocol === 'https:' ? url.href : '#';
  } catch {
    return '#';
  }
}

function renderGrid() {
  const grid = document.getElementById('providerGrid');
  grid.replaceChildren();
  providers.forEach(provider => {
    const slug = safeProviderSlug(provider.slug);
    if (!slug) return;
    const card = document.createElement('div');
    card.className = 'provider-card';
    card.id = 'card-' + slug;
    const header = document.createElement('div');
    header.className = 'provider-head';
    const icon = document.createElement('span');
    icon.className = 'provider-icon';
    icon.textContent = String(provider.icon || '');
    const identity = document.createElement('div');
    identity.className = 'provider-info';
    const name = document.createElement('div');
    name.className = 'provider-name';
    name.textContent = String(provider.name || slug);
    const tier = document.createElement('span');
    const tierName = String(provider.tier || 'unknown').toLowerCase().replace(/[^a-z0-9_-]/g, '');
    tier.className = 'provider-tier tier-' + tierName;
    tier.textContent = tierName;
    identity.append(name, tier);
    header.append(icon, identity);
    const description = document.createElement('div');
    description.className = 'provider-desc';
    description.textContent = String(provider.description || '');
    const models = document.createElement('div');
    models.className = 'provider-models';
    (Array.isArray(provider.free_models) ? provider.free_models : []).forEach(model => {
      const tag = document.createElement('span');
      tag.className = 'model-chip';
      tag.textContent = String(model);
      models.append(tag);
    });
    const status = document.createElement('div');
    status.className = 'provider-status';
    const dot = document.createElement('span');
    dot.className = 'dot';
    dot.id = 'dot-' + slug;
    const label = document.createElement('span');
    label.className = 'label';
    label.id = 'lbl-' + slug;
    label.textContent = 'Not scanned';
    status.append(dot, label);
    const actions = document.createElement('div');
    actions.className = 'provider-actions';
    const signup = document.createElement('a');
    signup.href = safeProviderUrl(provider.signup_url);
    signup.target = '_blank';
    signup.rel = 'noopener noreferrer';
    signup.className = 'btn-action';
    signup.textContent = 'Get Key';
    const docs = document.createElement('a');
    docs.href = safeProviderUrl(provider.docs_url);
    docs.target = '_blank';
    docs.rel = 'noopener noreferrer';
    docs.className = 'btn-action';
    docs.textContent = 'Docs';
    const validate = document.createElement('button');
    validate.type = 'button';
    validate.className = 'btn-action';
    validate.textContent = 'Validate';
    validate.addEventListener('click', () => validateOne(slug));
    actions.append(signup, docs, validate);
    card.append(header, description, models, status, actions);
    grid.append(card);
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

async function validateAll() {
  const panel = document.getElementById('resultsPanel');
  const list = document.getElementById('resultsList');
  panel.style.display = 'block';
  list.textContent = 'Validating...';
  try {
    const response = await fetch(API + '/validate-all');
    const results = await response.json();
    list.replaceChildren();
    results.forEach(item => {
      const row = document.createElement('div');
      row.className = 'result-row';
      const icon = document.createElement('span');
      icon.className = 'result-icon';
      icon.textContent = String(item.icon || '');
      const name = document.createElement('span');
      name.className = 'result-name';
      name.textContent = String(item.name || item.slug || '');
      const badge = document.createElement('span');
      badge.className = 'result-badge ' + (item.valid ? 'badge-ok' : 'badge-fail');
      badge.textContent = item.valid ? 'VALID' : 'INVALID: ' + String(item.error || 'Unknown error');
      row.append(icon, name, badge);
      list.append(row);
    });
  } catch {
    list.textContent = 'Backend not connected';
  }
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
