"""AnyClaw Web Dashboard — แสดงสถานะ + ควบคุมระบบ.

รัน: python -m creator_app.anyclaw.dashboard
เปิด: http://localhost:8080

Features:
- แสดงสถานะ Provider ทั้งหมด
- ดู Agent Registry
- ทดสอบ Chat
- ดู Skills Summary
- Real-time status
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CK-NEXUS Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; }
.header { background: #161b22; padding: 20px 30px; border-bottom: 1px solid #30363d; }
.header h1 { font-size: 24px; color: #58a6ff; }
.header p { color: #8b949e; margin-top: 4px; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 16px; margin-top: 20px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
.card h2 { color: #58a6ff; font-size: 16px; margin-bottom: 12px; }
.card h3 { color: #8b949e; font-size: 12px; text-transform: uppercase; margin-bottom: 8px; }
.stat { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #21262d; }
.stat:last-child { border: none; }
.stat .label { color: #8b949e; }
.stat .value { color: #c9d1d9; font-weight: 600; }
.status-ok { color: #3fb950; }
.status-warn { color: #d29922; }
.status-error { color: #f85149; }
.agent-list { list-style: none; }
.agent-list li { padding: 8px 0; border-bottom: 1px solid #21262d; display: flex; align-items: center; gap: 8px; }
.agent-list li:last-child { border: none; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot-green { background: #3fb950; }
.dot-red { background: #f85149; }
.dot-yellow { background: #d29922; }
.chat-box { margin-top: 16px; }
.chat-box textarea { width: 100%; height: 80px; background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 10px; border-radius: 6px; font-family: inherit; resize: vertical; }
.chat-box button { margin-top: 8px; background: #238636; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.chat-box button:hover { background: #2ea043; }
.chat-response { margin-top: 12px; padding: 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; min-height: 40px; white-space: pre-wrap; font-size: 13px; }
.skill-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
.skill-tag { background: #1f2937; padding: 6px 10px; border-radius: 4px; font-size: 12px; border: 1px solid #30363d; }
</style>
</head>
<body>
<div class="header">
  <h1>🧠 CK-NEXUS Dashboard</h1>
  <p>AnyClaw Super-Intelligent Mode — Agent Bridge + MCP Hub</p>
</div>
<div class="container">
  <div class="grid">
    <div class="card" id="status-card">
      <h2>📊 System Status</h2>
      <div id="status-content">Loading...</div>
    </div>
    <div class="card" id="agents-card">
      <h2>🤖 Agents</h2>
      <ul class="agent-list" id="agents-content">Loading...</ul>
    </div>
    <div class="card" id="providers-card">
      <h2>🔑 Providers</h2>
      <div id="providers-content">Loading...</div>
    </div>
    <div class="card" id="chat-card" style="grid-column: 1 / -1;">
      <h2>💬 Chat Test</h2>
      <div class="chat-box">
        <textarea id="chat-input" placeholder="พิมพ์คำถามที่นี่..."></textarea>
        <button onclick="sendChat()">ส่ง</button>
      </div>
      <div class="chat-response" id="chat-response"></div>
    </div>
    <div class="card" id="skills-card" style="grid-column: 1 / -1;">
      <h2>🛠️ Skills (50+)</h2>
      <div class="skill-grid" id="skills-content">Loading...</div>
    </div>
  </div>
</div>
<script>
async function loadData() {
  try {
    const status = await fetch('/api/status').then(r => r.json());
    document.getElementById('status-content').innerHTML = `
      <div class="stat"><span class="label">Mode</span><span class="value">${status.anyclaw?.mode || 'super'}</span></div>
      <div class="stat"><span class="label">Total Chats</span><span class="value">${status.anyclaw?.total_chats || 0}</span></div>
      <div class="stat"><span class="label">Cache</span><span class="value">${status.anyclaw?.cache_size || 0} entries</span></div>
      <div class="stat"><span class="label">Agents Available</span><span class="value status-ok">${status.agents?.available || 0}/${status.agents?.total_agents || 0}</span></div>
      <div class="stat"><span class="label">Hub Tools</span><span class="value">${status.hub?.total_tools || 0}</span></div>
    `;

    const agents = status.agents?.agents || {};
    let agentHtml = '';
    for (const [name, info] of Object.entries(agents)) {
      const cls = info.available ? 'dot-green' : 'dot-red';
      agentHtml += `<li><span class="dot ${cls}"></span>${name} <span style="color:#8b949e;font-size:11px">${info.category}</span></li>`;
    }
    document.getElementById('agents-content').innerHTML = agentHtml || '<li>No agents found</li>';

    const free = status.anyclaw?.free_providers_available || [];
    let provHtml = '';
    free.forEach(p => { provHtml += `<div class="stat"><span class="label">${p}</span><span class="value status-ok">✅ Active</span></div>`; });
    const claude = status.anyclaw?.claude_available;
    provHtml += `<div class="stat"><span class="label">Claude API</span><span class="value ${claude ? 'status-ok' : 'status-warn'}">${claude ? '✅' : '⚠️ No Key'}</span></div>`;
    document.getElementById('providers-content').innerHTML = provHtml;

    const skills = [
      'Universal System','Policy Engine','State Manager','Blind Vault','Multi-Key Pool',
      'Health Monitor','Auto-Provision','Secret Shield','Permission Gate','Audit Log',
      'Smart Cache','Auto Router','Parallel Executor','Self-Correction','Multi-Perspective',
      'Semantic Memory','Director','Engineer','Guardian','Analyst',
      'Researcher','Designer','Connector','Groq','OpenAI',
      'Google AI','Ollama','Telegram Bot','Webhook','MCP Server',
      'SD Card Manager','AnyClaw Core','Agent Registry','Local Model Bridge','MCP Hub',
      'Shell/Bash','Git/GitHub','File Ops','Code Analysis','Web Search',
      'Playwright','Image Gen','Security Scan','Vercel Deploy','Supabase',
      'Composio','Groq Adapter','OpenAI Adapter','Google Adapter','Ollama Adapter',
    ];
    document.getElementById('skills-content').innerHTML = skills.map(s =>
      `<div class="skill-tag">${s}</div>`
    ).join('');
  } catch(e) { console.error(e); }
}

async function sendChat() {
  const input = document.getElementById('chat-input').value;
  const response = document.getElementById('chat-response');
  if (!input) return;
  response.textContent = '⏳ กำลังคิด...';
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: input, mode: 'super'}),
    });
    const data = await res.json();
    response.textContent = `[${data.provider}] ${data.content}\\n\\n⏱️ ${data.latency_ms}ms`;
  } catch(e) {
    response.textContent = '❌ Error: ' + e.message;
  }
}

loadData();
setInterval(loadData, 30000);
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())
        elif parsed.path == "/api/status":
            self._json_response(self._get_status())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/chat":
            body = self._read_body()
            message = body.get("message", "")
            if not message:
                self._json_response({"error": "message required"}, 400)
                return
            from creator_app.anyclaw.core import AnyClawCore
            claw = AnyClawCore(mode=body.get("mode", "super"))
            resp = claw.chat(message)
            self._json_response({
                "content": resp.content,
                "provider": resp.provider,
                "latency_ms": round(resp.latency_ms, 1),
            })
        else:
            self.send_response(404)
            self.end_headers()

    def _get_status(self) -> dict:
        from creator_app.anyclaw.bridge.agent_registry import AgentRegistry
        from creator_app.anyclaw.core import AnyClawCore
        from creator_app.anyclaw.hub.mcp_hub import MCPHub
        claw = AnyClawCore(mode="super")
        reg = AgentRegistry()
        reg.scan()
        hub = MCPHub()
        return {
            "anyclaw": claw.status(),
            "agents": reg.status(),
            "hub": hub.status(),
        }

    def _json_response(self, data: dict, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return {}

    def log_message(self, format: str, *args: object) -> None:
        pass


def run_dashboard(port: int = 8080) -> None:
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"🌐 Dashboard running on http://localhost:{port}")
    print("   Ctrl+C เพื่อหยุด")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
        server.server_close()


if __name__ == "__main__":
    run_dashboard()
