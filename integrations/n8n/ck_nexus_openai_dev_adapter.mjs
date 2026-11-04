import http from 'node:http';

const HOST = process.env.CK_NEXUS_INTELLIGENCE_HOST || '127.0.0.1';
const PORT = Number(process.env.CK_NEXUS_INTELLIGENCE_PORT || 8767);
const TOKEN = process.env.CK_NEXUS_INTELLIGENCE_TOKEN || '';
const API_KEY = process.env.OPENAI_API_KEY || '';
const MODEL = process.env.CK_NEXUS_OPENAI_MODEL || '';
const API_URL = process.env.CK_NEXUS_OPENAI_RESPONSES_URL || 'https://api.openai.com/v1/responses';

function send(res, code, body) {
  res.writeHead(code, {'content-type':'application/json','cache-control':'no-store'});
  res.end(JSON.stringify(body));
}

function authorized(req) {
  if (!TOKEN) return false;
  return String(req.headers.authorization || '') === `Bearer ${TOKEN}`;
}

function extractOutputText(response) {
  if (typeof response.output_text === 'string' && response.output_text) return response.output_text;
  const texts = [];
  for (const item of response.output || []) {
    if (item?.type !== 'message') continue;
    for (const content of item.content || []) {
      if (content?.type === 'output_text' && typeof content.text === 'string') texts.push(content.text);
    }
  }
  return texts.join('\n');
}

function buildInput(body) {
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

async function invoke(body) {
  if (!API_KEY) throw new Error('openai_api_key_not_configured');
  if (!MODEL) throw new Error('openai_model_not_configured');
  const response = await fetch(API_URL, {
    method:'POST',
    headers:{'authorization':`Bearer ${API_KEY}`,'content-type':'application/json'},
    body:JSON.stringify({
      model:MODEL,
      input:buildInput(body),
      store:false,
      text:{verbosity:'medium'}
    }),
    signal:AbortSignal.timeout(120000)
  });
  const raw = await response.text();
  let parsed;
  try { parsed = JSON.parse(raw); } catch { parsed = {raw}; }
  if (!response.ok) throw new Error(`openai_${response.status}`);
  const text = extractOutputText(parsed).trim();
  if (!text) throw new Error('openai_empty_output');
  try {
    return JSON.parse(text);
  } catch {
    return {type:'final',verdict:'PROPOSAL',result:{output:text,parse_status:'non_json_fallback'},observed:[],inferred:[],risks:['structured_output_parse_failed'],next_action:'review_output_and_retry_with_stricter_format'};
  }
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    return send(res, 200, {ok:true,service:'ck-nexus-openai-dev-adapter',mode:'development_only',api_key_configured:Boolean(API_KEY),model_configured:Boolean(MODEL),model:MODEL || null});
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
      send(res,200,{...result,production_mutation:false,production_ready:false,q10_q11_q12_evidence:false});
    } catch (error) {
      send(res,400,{error:String(error.message || error),mode:'fail_closed',production_mutation:false});
    }
  });
});

server.listen(PORT, HOST, () => console.log(`CK-NEXUS OpenAI dev adapter listening on http://${HOST}:${PORT}`));
