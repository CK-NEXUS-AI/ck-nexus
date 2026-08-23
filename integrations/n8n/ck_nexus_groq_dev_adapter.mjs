import http from 'node:http';

const HOST = process.env.CK_NEXUS_INTELLIGENCE_HOST || '127.0.0.1';
const PORT = Number(process.env.CK_NEXUS_INTELLIGENCE_PORT || 8767);
const TOKEN = process.env.CK_NEXUS_INTELLIGENCE_TOKEN || '';
const API_KEY = process.env.GROQ_API_KEY || '';
const MODEL = process.env.CK_NEXUS_GROQ_MODEL || 'openai/gpt-oss-120b';
const API_URL = process.env.CK_NEXUS_GROQ_URL || 'https://api.groq.com/openai/v1/chat/completions';

function send(res, code, body) {
  res.writeHead(code, {'content-type':'application/json','cache-control':'no-store'});
  res.end(JSON.stringify(body));
}

function authorized(req) {
  return Boolean(TOKEN) && String(req.headers.authorization || '') === `Bearer ${TOKEN}`;
}

function buildPrompt(body) {
  const trace = Array.isArray(body.tool_trace) ? body.tool_trace : [];
  return [
    'You are a CK-NEXUS DEVELOPMENT specialist. CK-NEXUS Governor is the sole authority.',
    'Never claim Production Ready, Q10/Q11/Q12 PASS, merge authority, deployment authority, or secret access.',
    'Return ONLY valid JSON. Do not reveal private chain-of-thought. Use concise observable rationale.',
    'If a repository/test tool is needed, return exactly:',
    '{"type":"tool_request","tool":"<allowed tool>","args":{...}}',
    'When finished, return:',
    '{"type":"final","verdict":"PASS|FAIL|BLOCKED|PROPOSAL","result":{...},"observed":[],"inferred":[],"risks":[],"next_action":"..."}',
    `Mission ID: ${body.mission_id || 'unknown'}`,
    `Phase: ${body.phase || 'unknown'}`,
    `Role: ${body.role || 'unknown'}`,
    `Skills: ${JSON.stringify(body.skills || [])}`,
    `Branch: ${body.branch || 'unknown'}`,
    `Prompt: ${body.prompt || ''}`,
    `Allowed tools: ${JSON.stringify(body?.tool_protocol?.allowed_tools || [])}`,
    `Previous tool trace: ${JSON.stringify(trace)}`
  ].join('\n');
}

function safeUpstreamError(status, parsed) {
  const err = parsed?.error || {};
  return {
    error:'groq_upstream_error',
    provider:'groq',
    upstream_status:status,
    upstream_type:typeof err.type === 'string' ? err.type : null,
    upstream_code:typeof err.code === 'string' ? err.code : null,
    upstream_param:typeof err.param === 'string' ? err.param : null,
    mode:'fail_closed',
    production_mutation:false,
    production_ready:false
  };
}

async function invoke(body) {
  if (!API_KEY) throw new Error('groq_api_key_not_configured');
  const response = await fetch(API_URL, {
    method:'POST',
    headers:{'authorization':`Bearer ${API_KEY}`,'content-type':'application/json'},
    body:JSON.stringify({
      model:MODEL,
      messages:[{role:'user',content:buildPrompt(body)}],
      response_format:{type:'json_object'},
      temperature:0,
      max_completion_tokens:2048
    }),
    signal:AbortSignal.timeout(120000)
  });
  const raw = await response.text();
  let parsed;
  try { parsed = JSON.parse(raw); } catch { parsed = {}; }
  if (!response.ok) return {__upstream_error:safeUpstreamError(response.status, parsed)};
  const text = String(parsed?.choices?.[0]?.message?.content || '').trim();
  if (!text) throw new Error('groq_empty_output');
  try { return JSON.parse(text); }
  catch {
    return {
      type:'final',verdict:'PROPOSAL',
      result:{output:text,parse_status:'non_json_fallback'},
      observed:[],inferred:[],risks:['structured_output_parse_failed'],
      next_action:'review_output_and_retry_with_stricter_format'
    };
  }
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    return send(res, 200, {
      ok:true,service:'ck-nexus-groq-dev-adapter',provider:'groq',mode:'development_only',
      api_key_configured:Boolean(API_KEY),model_configured:Boolean(MODEL),model:MODEL,
      production_mutation:false,production_ready:false
    });
  }
  if (req.method !== 'POST' || req.url !== '/v1/intelligence') return send(res,404,{error:'not_found'});
  if (!authorized(req)) return send(res,401,{error:'intelligence_token_required',mode:'fail_closed'});
  let raw='';
  req.on('data', chunk => { raw += chunk; if (raw.length > 512 * 1024) req.destroy(); });
  req.on('end', async () => {
    try {
      const body=JSON.parse(raw || '{}');
      if (body.allow_production_mutation === true || body.allow_secret_export === true) throw new Error('authority_violation');
      const result=await invoke(body);
      if (result?.__upstream_error) return send(res,502,result.__upstream_error);
      send(res,200,{...result,provider:'groq',production_mutation:false,production_ready:false,q10_q11_q12_evidence:false});
    } catch (error) {
      send(res,400,{error:String(error.message || error),provider:'groq',mode:'fail_closed',production_mutation:false,production_ready:false});
    }
  });
});

server.listen(PORT, HOST, () => console.log(`CK-NEXUS Groq dev adapter listening on http://${HOST}:${PORT}`));
