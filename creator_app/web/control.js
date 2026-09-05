const state = { manifest: null, status: null, development: null };
const tokenInput = document.querySelector('#access-token');
tokenInput.value = sessionStorage.getItem('cknexus_access_token') || '';

function authHeaders() {
  const token = sessionStorage.getItem('cknexus_access_token') || '';
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function api(path) {
  const response = await fetch(path, { headers: { Accept: 'application/json', ...authHeaders() } });
  const kind = response.headers.get('content-type') || '';
  const body = kind.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) throw new Error(`${response.status} ${typeof body === 'object' ? JSON.stringify(body) : body}`);
  return body;
}

function valueText(value) {
  if (value === true) return 'READY';
  if (value === false) return 'OFF / BLOCKED';
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
}

function statusCard(label, value, detail = '') {
  const item = document.createElement('article');
  item.className = 'status-item';
  const labelEl = document.createElement('span');
  labelEl.textContent = label;
  const strong = document.createElement('strong');
  strong.textContent = valueText(value);
  if (value === true || String(value).toLowerCase() === 'ready') strong.classList.add('ok');
  if (value === false || String(value).toLowerCase().includes('blocked')) strong.classList.add('bad');
  const small = document.createElement('small');
  small.textContent = detail || 'CK-NEXUS runtime';
  item.append(labelEl, strong, small);
  return item;
}

function renderManifest(manifest) {
  state.manifest = manifest;
  document.querySelector('#group-count').textContent = String(manifest.groups.length).padStart(2, '0');
  document.querySelector('#route-count').textContent = String(manifest.route_count).padStart(2, '0');
  const grid = document.querySelector('#control-grid');
  const template = document.querySelector('#group-template');
  grid.replaceChildren();

  manifest.groups.forEach((group, index) => {
    const fragment = template.content.cloneNode(true);
    const toggle = fragment.querySelector('.control-toggle');
    const detail = fragment.querySelector('.control-detail');
    fragment.querySelector('.index').textContent = String(index + 1).padStart(2, '0');
    fragment.querySelector('.title').textContent = group.title;
    fragment.querySelector('.summary-copy').textContent = group.summary;
    fragment.querySelector('.count').textContent = `${group.route_count} routes`;
    fragment.querySelector('.deep-link').href = group.deep_link || '/docs';

    const routeList = fragment.querySelector('.route-list');
    if (!group.routes.length) {
      const row = document.createElement('div');
      row.className = 'module';
      const code = document.createElement('code');
      code.textContent = 'Internal service/module — no direct HTTP route.';
      row.append(code);
      routeList.append(row);
    }
    group.routes.forEach((route) => {
      const row = document.createElement('div');
      row.className = 'route';
      const method = document.createElement('span');
      method.className = 'method';
      method.textContent = route.methods.join(' / ') || 'ROUTE';
      const code = document.createElement('code');
      code.textContent = route.path;
      const docs = document.createElement('a');
      docs.href = '/docs';
      docs.textContent = 'OPEN API';
      row.append(method, code, docs);
      routeList.append(row);
    });

    const moduleList = fragment.querySelector('.module-list');
    group.modules.forEach((modulePath) => {
      const row = document.createElement('div');
      row.className = 'module';
      const code = document.createElement('code');
      code.textContent = modulePath;
      row.append(code);
      moduleList.append(row);
    });

    toggle.addEventListener('click', () => {
      const open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!open));
      detail.hidden = open;
    });
    grid.append(fragment);
  });
}

function renderStatus(snapshot) {
  state.status = snapshot;
  const dbReady = Boolean(snapshot.database?.ready);
  const aiReady = Boolean(snapshot.ai?.ready);
  document.querySelector('#db-state').textContent = dbReady ? 'READY' : 'DEGRADED';
  document.querySelector('#ai-state').textContent = aiReady ? 'READY' : 'LIMITED';
  document.querySelector('#system-state').textContent = dbReady ? 'CONTROL ONLINE' : 'DEGRADED';
  document.querySelector('#system-state').className = dbReady ? 'ok' : 'bad';
  document.querySelector('#system-detail').textContent = `${snapshot.environment} / v${snapshot.version}`;
  document.querySelector('#status-time').textContent = new Date().toLocaleString();

  document.querySelector('#status-grid').replaceChildren(
    statusCard('DATABASE', dbReady, 'required persistence'),
    statusCard('AI PREFERRED', snapshot.ai?.preferred || 'none', `${snapshot.ai?.providers ?? 0} provider(s)`),
    statusCard('AGNES', snapshot.skills?.agnes_enabled, `${snapshot.skills?.skill_count ?? 0} skill(s)`),
    statusCard('PHASE 3', snapshot.skills?.phase3_enabled, 'hardened pipeline'),
    statusCard('DEV COUNCIL', snapshot.development?.council_ready, 'multi-role advisory runtime'),
    statusCard('CODEX', snapshot.development?.codex_ready, 'gated development execution'),
    statusCard('CONNECTOR FABRIC', snapshot.integrations?.dynamic_connector_fabric, `${snapshot.integrations?.dynamic_connector_count ?? 0} connector(s)`),
    statusCard('CREDENTIAL VAULT', snapshot.security?.credential_vault_enabled, snapshot.security?.secrets_exposed ? 'unsafe' : 'secrets redacted'),
    statusCard('EMAIL GATEWAY', snapshot.email?.enabled, 'ingress / routing / outbox'),
    statusCard('ACCESS CONTROL', snapshot.security?.access_token_required ? 'TOKEN REQUIRED' : 'LOCAL OPEN', 'authorization boundary'),
    statusCard('RUNTIME BINDING', snapshot.operations?.runtime_binding_required, 'PostgreSQL / Redis binding'),
    statusCard('METRICS', snapshot.operations?.metrics_enabled, 'observability endpoint')
  );
}


function renderDevelopment(snapshot) {
  state.development = snapshot;
  const counts = snapshot.task_counts || {};
  const competency = snapshot.competency || {};
  const release = snapshot.release_authority || {};
  const scores = snapshot.scores || {};
  const grid = document.querySelector('#development-status-grid');
  grid.replaceChildren(
    statusCard('COMPLETED', counts.completed ?? 0, 'reviewed + merged only'),
    statusCard('ACTIVE', counts.active ?? 0, 'running / measured / review required'),
    statusCard('QUEUED', counts.queued ?? 0, 'received / planned / queued'),
    statusCard('BLOCKED', counts.blocked ?? 0, 'reason required'),
    statusCard(
      'AI PRO-LEVEL',
      competency.pro_level_write_enabled ?? 0,
      `${competency.total ?? 0} assessed`
    ),
    statusCard(
      'AI OBSERVER / PENDING',
      competency.observer_or_pending ?? 0,
      'read / comment only'
    ),
    statusCard('Q10', release.q10 || 'UNKNOWN', release.source || 'authority source'),
    statusCard('Q11', release.q11 || 'UNKNOWN', 'production closure'),
    statusCard('Q12', release.q12 || 'UNKNOWN', 'production closure'),
    statusCard('PRODUCTION', release.production || 'UNKNOWN', 'authority effect: none'),
    statusCard(
      'OPENSSF',
      scores.openssf_scorecard_current ?? 'UNKNOWN',
      `target ${scores.openssf_scorecard_target ?? 'UNKNOWN'}`
    )
  );

  const next = snapshot.next_task;
  document.querySelector('#development-next').textContent = next
    ? `NEXT TASK: ${next.task_id} / ${next.title} / ${next.state} / ${next.priority}`
    : 'NEXT TASK: NONE';
}

async function refresh() {
  const button = document.querySelector('#refresh-all');
  button.disabled = true;
  button.textContent = 'REFRESHING';
  try {
    const [manifest, snapshot, development] = await Promise.all([
      api('/api/control/manifest'),
      api('/api/control/status'),
      api('/api/control/development/live')
    ]);
    renderManifest(manifest);
    renderStatus(snapshot);
    renderDevelopment(development);
  } catch (error) {
    document.querySelector('#system-state').textContent = 'AUTH / API ERROR';
    document.querySelector('#system-state').className = 'bad';
    document.querySelector('#system-detail').textContent = error.message;
    const grid = document.querySelector('#control-grid');
    grid.replaceChildren();
    const message = document.createElement('p');
    message.className = 'loading';
    message.textContent = 'ใส่ ACCESS TOKEN ให้ถูกต้อง แล้วกด REFRESH ALL';
    grid.append(message);
  } finally {
    button.disabled = false;
    button.textContent = 'REFRESH ALL';
  }
}

document.querySelector('#save-token').addEventListener('click', () => {
  const token = tokenInput.value.trim();
  if (token) sessionStorage.setItem('cknexus_access_token', token);
  else sessionStorage.removeItem('cknexus_access_token');
  refresh();
window.setInterval(refresh, 5000);
});
document.querySelector('#refresh-all').addEventListener('click', refresh);
refresh();
