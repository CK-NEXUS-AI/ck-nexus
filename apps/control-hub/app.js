const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const toast = $('#toast');
const showToast = (message) => {
  toast.textContent = message;
  toast.classList.add('show');
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove('show'), 2200);
};

const mobileNav = $('#mobile-nav');
const menuToggle = $('#menu-toggle');
menuToggle?.addEventListener('click', () => {
  const open = menuToggle.getAttribute('aria-expanded') === 'true';
  menuToggle.setAttribute('aria-expanded', String(!open));
  mobileNav.hidden = open;
});

$$('.mobile-nav a').forEach((link) => link.addEventListener('click', () => {
  mobileNav.hidden = true;
  menuToggle?.setAttribute('aria-expanded', 'false');
}));

const commandDialog = $('#command-dialog');
const approvalDialog = $('#approval-dialog');

const openDialog = (dialog) => {
  if (!dialog) return;
  if (typeof dialog.showModal === 'function') dialog.showModal();
};

$('#open-command')?.addEventListener('click', () => openDialog(commandDialog));
$('#new-goal')?.addEventListener('click', () => openDialog(commandDialog));
$('#open-approvals')?.addEventListener('click', () => {
  document.querySelector('#approvals')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
});

const approvalDetails = {
  credential: {
    action: 'Reconnect provider credential',
    risk: 'MEDIUM / owner OAuth required',
    target: 'Provider connection',
    reversible: 'Yes — connection can be revoked',
  },
  security: {
    action: 'Change repository security settings',
    risk: 'HIGH / protected configuration',
    target: 'Canonical GitHub repository',
    reversible: 'Usually, but policy/evidence impact must be reviewed',
  },
};

$$('.approval-open').forEach((button) => button.addEventListener('click', () => {
  const detail = approvalDetails[button.dataset.approval];
  if (!detail) return;
  $('#dialog-action').textContent = detail.action;
  $('#dialog-risk').textContent = detail.risk;
  $('#dialog-target').textContent = detail.target;
  $('#dialog-reversible').textContent = detail.reversible;
  openDialog(approvalDialog);
}));

const probeJson = async (url) => {
  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
    credentials: 'same-origin',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error(`${response.status}`);
  return response.json();
};

const refreshHealth = async () => {
  const value = $('#health-value');
  const detail = $('#health-detail');
  value.textContent = 'CHECKING';
  detail.textContent = 'runtime probe';
  try {
    const health = await probeJson('/health');
    const state = String(health.status || health.state || 'READY').toUpperCase();
    value.textContent = state;
    detail.textContent = 'live /health response';
    value.className = state === 'READY' || state === 'OK' || state === 'HEALTHY' ? 'good' : '';
  } catch (error) {
    value.textContent = 'PROTOTYPE';
    detail.textContent = 'standalone shell; runtime not bound';
    value.className = 'muted';
  }
};

const refreshConnectors = async () => {
  try {
    const payload = await probeJson('/api/integrations/status');
    const source = payload.integrations || payload.providers || payload;
    if (!source || typeof source !== 'object') return;
    const rows = Object.entries(source).slice(0, 8).map(([name, raw]) => {
      const object = raw && typeof raw === 'object' ? raw : { status: raw };
      const status = String(object.status || object.state || 'UNKNOWN').toUpperCase();
      const className = ['READY', 'OK', 'HEALTHY', 'CONNECTED'].includes(status) ? 'good' : 'muted';
      return `<li><span>${escapeHtml(name)}</span><strong class="${className}">${escapeHtml(status)}</strong></li>`;
    });
    if (rows.length) $('#connector-list').innerHTML = rows.join('');
  } catch (_) {
    // Prototype fixture remains visible. Unknown connectivity is not converted to success.
  }
};

const escapeHtml = (value) => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;');

const refreshAll = async () => {
  await Promise.allSettled([refreshHealth(), refreshConnectors()]);
  showToast('State refresh complete');
};

$('#refresh-state')?.addEventListener('click', refreshAll);

$$('a[href^="#"]').forEach((link) => link.addEventListener('click', () => {
  const href = link.getAttribute('href');
  if (!href || href === '#') return;
  $$('.primary-nav a').forEach((item) => item.removeAttribute('aria-current'));
  const primaryMatch = $(`.primary-nav a[href="${href}"]`);
  if (primaryMatch) primaryMatch.setAttribute('aria-current', 'page');
}));

[commandDialog, approvalDialog].forEach((dialog) => {
  dialog?.addEventListener('close', () => showToast('Prototype action closed without side effect'));
});

refreshAll();
