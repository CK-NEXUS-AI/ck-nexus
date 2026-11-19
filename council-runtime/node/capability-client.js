'use strict';
class CapabilityClient {
  constructor({ authorityUrl, serviceToken, handlers = new Map() }) {
    this.authorityUrl = authorityUrl.replace(/\/$/, ''); this.serviceToken = serviceToken; this.handlers = handlers;
  }
  async _post(path, body) {
    const res = await fetch(`${this.authorityUrl}${path}`, { method:'POST', headers:{'content-type':'application/json','authorization':`Bearer ${this.serviceToken}`}, body:JSON.stringify(body) });
    const data = await res.json(); if (!res.ok) { const e=new Error(data.message||data.error||'authority denied'); e.code=data.error||`HTTP_${res.status}`; throw e; } return data;
  }
  async invoke(capabilityId, params = {}, ctx = {}) {
    if (ctx.taskId !== undefined && (typeof ctx.taskId !== 'string' || !ctx.taskId.trim())) throw Object.assign(new Error('taskId must be a non-empty string'), {code:'INVALID_TASK_SCOPE'});
    const decision = await this._post('/v1/enforce', { capabilityId, params, ctx });
    const handler = this.handlers.get(capabilityId); if (!handler) throw Object.assign(new Error('no local handler registered'), {code:'NO_HANDLER'});
    const consumed = await this._post('/v1/grants/consume', { executionGrant: decision.executionGrant, params, expectedTaskId: ctx.taskId });
    if (!consumed.ok) throw Object.assign(new Error('execution grant rejected'), {code:'GRANT_REJECTED'});
    return handler(params, { ...ctx, executionGrant: decision.executionGrant });
  }
  resolveDecision(body) { return this._post('/v1/resolve', body); }
}
module.exports = { CapabilityClient };
