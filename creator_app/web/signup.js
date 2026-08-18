let providers = [];
let scanResults = [];

async function init() {
  try {
    const resp = await fetch('/api/providers');
    providers = await resp.json();
  } catch (e) {
    providers = getDefaultProviders();
  }
  renderProviders();
  populateSelect();
  autoScan();
}

function getDefaultProviders() {
  return [
    { name: "Groq", slug: "groq", icon: "⚡", tier: "free", env_key: "GROQ_API_KEY", description: "Fast inference, generous free tier", free_models: ["llama-3.3-70b-versatile", "gemma2-9b-it"], signup_url: "https://console.groq.com/keys" },
    { name: "Cerebras", slug: "cerebras", icon: "🧠", tier: "free", env_key: "CEREBRAS_API_KEY", description: "Ultra-fast inference speeds", free_models: ["llama-3.3-70b", "llama-3.1-8b"], signup_url: "https://cloud.cerebras.ai/" },
    { name: "OpenRouter", slug: "openrouter", icon: "🔀", tier: "free", env_key: "OPENROUTER_API_KEY", description: "Gateway to 100+ models, many free", free_models: ["meta-llama/llama-3.3-70b-instruct:free", "qwen/qwen-2.5-72b-instruct:free"], signup_url: "https://openrouter.ai/keys" },
    { name: "Google Gemini", slug: "gemini", icon: "💎", tier: "free", env_key: "GEMINI_API_KEY", description: "Google's latest models, free tier", free_models: ["gemini-2.0-flash", "gemini-1.5-flash"], signup_url: "https://aistudio.google.com/apikey" },
    { name: "DeepSeek", slug: "deepseek", icon: "🔍", tier: "free", env_key: "DEEPSEEK_API_KEY", description: "Strong reasoning, free credits", free_models: ["deepseek-chat", "deepseek-reasoner"], signup_url: "https://platform.deepseek.com/" },
    { name: "Together AI", slug: "together", icon: "🤝", tier: "free", env_key: "TOGETHER_API_KEY", description: "Open-source model hosting", free_models: ["meta-llama/Llama-3-70b-chat-hf"], signup_url: "https://api.together.xyz/settings/api-keys" },
    { name: "Mistral AI", slug: "mistral", icon: "🌊", tier: "free", env_key: "MISTRAL_API_KEY", description: "European AI, free tier", free_models: ["mistral-small-latest"], signup_url: "https://console.mistral.ai/api-keys/" },
    { name: "SambaNova", slug: "sambanova", icon: "🔥", tier: "free", env_key: "SAMBANOVA_API_KEY", description: "Enterprise-grade, free tier", free_models: ["Meta-Llama-3.3-70B-Instruct"], signup_url: "https://cloud.sambanova.ai/apis" },
    { name: "Fireworks AI", slug: "fireworks", icon: "🎆", tier: "free", env_key: "FIREWORKS_API_KEY", description: "Fast inference, free tier", free_models: ["accounts/fireworks/models/llama-v3p3-70b-instruct"], signup_url: "https://fireworks.ai/account/api-keys" },
    { name: "Cloudflare", slug: "cloudflare", icon: "☁️", tier: "free", env_key: "CLOUDFLARE_API_TOKEN", description: "Edge AI, generous free tier", free_models: ["@cf/meta/llama-3.3-70b-instruct-fp8"], signup_url: "https://dash.cloudflare.com/profile/api-tokens" },
    { name: "xAI (Grok)", slug: "xai", icon: "✖️", tier: "free", env_key: "XAI_API_KEY", description: "Elon Musk's AI, free credits", free_models: ["grok-2-1212"], signup_url: "https://console.x.ai/" },
    { name: "Cohere", slug: "cohere", icon: "📊", tier: "free", env_key: "COHERE_API_KEY", description: "RAG-optimized, free tier", free_models: ["command-r", "command-r-plus"], signup_url: "https://dashboard.cohere.com/api-keys" },
    { name: "Novita AI", slug: "novita", icon: "🚀", tier: "free", env_key: "NOVITA_API_KEY", description: "Uncensored models, free tier", free_models: ["meta-llama/llama-3.3-70b-instruct"], signup_url: "https://novita.ai/settings" },
    { name: "Chutes AI", slug: "chutes", icon: "🪂", tier: "free", env_key: "CHUTES_API_KEY", description: "Community-driven, free tier", free_models: ["chutesai/llama-3.3-70b-instruct"], signup_url: "https://chutes.ai/app/api-keys" },
    { name: "HuggingFace", slug: "huggingface", icon: "🤗", tier: "free", env_key: "HUGGINGFACE_API_KEY", description: "Open-source hub, free inference", free_models: ["meta-llama/Llama-3.3-70B-Instruct"], signup_url: "https://huggingface.co/settings/tokens" },
    { name: "OpenAI", slug: "openai", icon: "🤖", tier: "freemium", env_key: "OPENAI_API_KEY", description: "$5 free credit on signup", free_models: ["gpt-4o-mini"], signup_url: "https://platform.openai.com/api-keys" },
    { name: "Anthropic", slug: "anthropic", icon: "🏛️", tier: "freemium", env_key: "ANTHROPIC_API_KEY", description: "Claude models, free tier", free_models: ["claude-3-5-haiku-20241022"], signup_url: "https://console.anthropic.com/settings/keys" },
  ];
}

function renderProviders() {
  const grid = document.getElementById('providersGrid');
  grid.innerHTML = providers.map(p => `
    <div class="provider-card" id="card-${p.slug}">
      <div class="provider-header">
        <span class="provider-icon">${p.icon}</span>
        <div>
          <div class="provider-name">${p.name}</div>
          <span class="provider-tier tier-${p.tier}">${p.tier}</span>
        </div>
      </div>
      <div class="provider-desc">${p.description}</div>
      <div class="provider-models">
        ${(p.free_models || []).slice(0, 3).map(m => `<span class="model-tag">${m}</span>`).join('')}
      </div>
      <div class="provider-status">
        <div class="status-dot" id="dot-${p.slug}"></div>
        <span class="status-text" id="status-${p.slug}">Not scanned</span>
      </div>
      <div class="provider-actions">
        <a href="${p.signup_url}" target="_blank" class="btn btn-secondary btn-sm">🔑 Get Key</a>
        <button class="btn btn-info btn-sm" onclick="validateSingle('${p.slug}')">✅ Validate</button>
      </div>
    </div>
  `).join('');
}

function populateSelect() {
  const sel = document.getElementById('providerSelect');
  providers.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.slug;
    opt.textContent = `${p.icon} ${p.name}`;
    sel.appendChild(opt);
  });
}

async function autoScan() {
  const status = document.getElementById('scanStatus');
  status.textContent = '🔍 Auto-scanning environment...';
  try {
    const resp = await fetch('/api/providers/scan');
    scanResults = await resp.json();
    updateCards(scanResults);
    const found = scanResults.filter(r => r.has_key).length;
    status.textContent = `✅ Found ${found} key(s) out of ${scanResults.length} providers`;
  } catch (e) {
    status.textContent = '⚠️ Backend not connected — using local scan';
    localScan();
  }
}

function localScan() {
  const envKeys = {};
  const envNames = providers.map(p => p.env_key);
  scanResults = providers.map(p => ({
    slug: p.slug,
    name: p.name,
    icon: p.icon,
    has_key: false,
    key_preview: null,
  }));
  updateCards(scanResults);
}

function updateCards(results) {
  results.forEach(r => {
    const card = document.getElementById(`card-${r.slug}`);
    const dot = document.getElementById(`dot-${r.slug}`);
    const status = document.getElementById(`status-${r.slug}`);
    if (!card) return;
    if (r.has_key) {
      card.classList.add('has-key');
      dot.classList.add('active');
      status.textContent = `✅ Active (${r.key_preview})`;
      status.style.color = '#22c55e';
    } else {
      card.classList.remove('has-key');
      dot.classList.remove('active');
      status.textContent = '❌ No key found';
      status.style.color = '#ef4444';
    }
  });
}

async function scanProviders() {
  const btn = document.getElementById('scanBtn');
  const status = document.getElementById('scanStatus');
  btn.disabled = true;
  btn.textContent = '⏳ Scanning...';
  status.textContent = 'Scanning all providers...';

  document.querySelectorAll('.provider-card').forEach(c => c.classList.add('scanning'));

  try {
    const resp = await fetch('/api/providers/scan');
    scanResults = await resp.json();
    updateCards(scanResults);
    const found = scanResults.filter(r => r.has_key).length;
    status.textContent = `✅ Scan complete: ${found}/${scanResults.length} keys found`;
  } catch (e) {
    status.textContent = '❌ Backend not connected';
  }

  document.querySelectorAll('.provider-card').forEach(c => c.classList.remove('scanning'));
  btn.disabled = false;
  btn.textContent = '🔍 Scan Environment for API Keys';
}

async function validateSingle(slug) {
  const status = document.getElementById(`status-${slug}`);
  const dot = document.getElementById(`dot-${slug}`);
  status.textContent = '⏳ Validating...';
  status.style.color = '#eab308';

  try {
    const resp = await fetch(`/api/providers/${slug}/validate`);
    const result = await resp.json();
    if (result.valid) {
      status.textContent = `✅ Valid (${result.key_preview})`;
      status.style.color = '#22c55e';
      dot.classList.add('active');
      document.getElementById(`card-${slug}`).classList.add('has-key');
    } else {
      status.textContent = `❌ ${result.error}`;
      status.style.color = '#ef4444';
      dot.classList.remove('active');
    }
  } catch (e) {
    status.textContent = '❌ Backend not connected';
    status.style.color = '#ef4444';
  }
}

async function addKey() {
  const slug = document.getElementById('providerSelect').value;
  const key = document.getElementById('apiKeyInput').value;
  const result = document.getElementById('addResult');

  if (!slug || !key) {
    result.innerHTML = '<span style="color:#ef4444">⚠️ Select provider and enter API key</span>';
    return;
  }

  try {
    const resp = await fetch(`/api/providers/${slug}/set-key`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key }),
    });
    const data = await resp.json();
    if (data.success) {
      result.innerHTML = `<span style="color:#22c55e">✅ Key added for ${slug}</span>`;
      document.getElementById('apiKeyInput').value = '';
      scanProviders();
    } else {
      result.innerHTML = `<span style="color:#ef4444">❌ ${data.error}</span>`;
    }
  } catch (e) {
    result.innerHTML = '<span style="color:#ef4444">❌ Backend not connected</span>';
  }
}

async function validateAll() {
  const panel = document.getElementById('resultsPanel');
  const list = document.getElementById('resultsList');
  panel.style.display = 'block';
  list.innerHTML = '<p>⏳ Validating all keys...</p>';

  try {
    const resp = await fetch('/api/providers/validate-all');
    const results = await resp.json();
    list.innerHTML = results.map(r => `
      <div class="result-item">
        <span class="result-icon">${r.icon}</span>
        <span class="result-name">${r.name}</span>
        <span class="result-badge ${r.valid ? 'badge-valid' : 'badge-invalid'}">
          ${r.valid ? '✅ VALID' : '❌ ' + r.error}
        </span>
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = '<p>❌ Backend not connected</p>';
  }
}

function exportConfig() {
  const config = {
    version: "1.0",
    timestamp: new Date().toISOString(),
    providers: scanResults.filter(r => r.has_key).map(r => ({
      slug: r.slug,
      name: r.name,
      env_key: r.env_key,
      key_preview: r.key_preview,
    })),
  };
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ck-nexus-providers-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function generateEnv() {
  const panel = document.getElementById('envOutput');
  const content = document.getElementById('envContent');
  panel.style.display = 'block';

  let env = '# CK-NEXUS Provider Configuration\n';
  env += `# Generated: ${new Date().toISOString()}\n\n`;
  env += '# === Free LLM Providers ===\n\n';

  scanResults.forEach(r => {
    const provider = providers.find(p => p.slug === r.slug);
    env += `# ${r.icon} ${r.name} (${r.has_key ? 'ACTIVE' : 'NOT SET'})\n`;
    env += `# Get key: ${provider?.signup_url || ''}\n`;
    if (r.has_key) {
      env += `${r.env_key}=${r.key_preview}\n`;
    } else {
      env += `# ${r.env_key}=\n`;
    }
    env += '\n';
  });

  content.textContent = env;
}

function copyEnv() {
  const content = document.getElementById('envContent').textContent;
  navigator.clipboard.writeText(content).then(() => {
    const btn = event.target;
    btn.textContent = '✅ Copied!';
    setTimeout(() => btn.textContent = '📋 Copy', 2000);
  });
}

init();
