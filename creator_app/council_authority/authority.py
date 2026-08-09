from __future__ import annotations
import hashlib, hmac, json
from pathlib import Path
from typing import Any
from creator_app.credential_broker import CredentialId
from .storage import AuthorityStore

COST_WEIGHTS={"free":0,"low":1,"medium":5,"high":20}

class PolicyDenied(PermissionError):
    def __init__(self, code:str, message:str): super().__init__(message); self.code=code

def canonical_hash(params: dict) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()).hexdigest()

class BrokerScopeAdapter:
    def __init__(self, broker): self.broker=broker
    def check_scope(self, consumer: str, credential_ref: str) -> bool:
        try: cid=CredentialId(credential_ref)
        except ValueError: return False
        return self.broker.is_allowed(cid, consumer=consumer) and self.broker.is_configured(cid, consumer=consumer)

class CapabilityAuthority:
    def __init__(self, contract:dict, *, store:AuthorityStore, broker_adapter, grant_secret:bytes, default_budget:int=100):
        self._validate_contract(contract); self.contract=contract; self.store=store; self.broker=broker_adapter; self.default_budget=default_budget
        if len(grant_secret)<32: raise ValueError("grant secret must be at least 32 bytes")
        self.grant_secret=grant_secret; self.policy_sha256=hashlib.sha256(json.dumps(contract,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    @classmethod
    def from_file(cls,path:str,**kwargs): return cls(json.loads(Path(path).read_text()),**kwargs)
    @staticmethod
    def _validate_contract(c:dict):
        if set(c)-{"version","capabilities","agents"}: raise ValueError("unknown top-level policy fields")
        for key in ("version","capabilities","agents"):
            if key not in c: raise ValueError(f"missing policy field: {key}")
        for cid,cap in c["capabilities"].items():
            if cap.get("costClass") not in COST_WEIGHTS: raise ValueError(f"invalid costClass for {cid}")
        for aid,a in c["agents"].items():
            if not isinstance(a.get("permissions"),list): raise ValueError(f"permissions missing for {aid}")
    def _permitted(self,agent_id,capability_id):
        a=self.contract["agents"].get(agent_id) or {}
        return any(p==capability_id or (p.endswith("*") and capability_id.startswith(p[:-1])) for p in a.get("permissions",[]))
    def enforce(self, identity, capability_id:str, params:dict, ctx:dict|None=None)->dict:
        ctx=ctx or {}; agent_id=identity.agent_id; cap=self.contract["capabilities"].get(capability_id)
        def deny(code,msg): self.store.append_audit({"type":"capability_check","status":"DENIED","code":code,"agent_id":agent_id,"capability_id":capability_id,"task_id":ctx.get("taskId"),"policy_sha256":self.policy_sha256}); raise PolicyDenied(code,msg)
        if not cap: deny("NOT_REGISTERED","capability is not registered")
        if not self._permitted(agent_id,capability_id): deny("NO_PERMISSION","agent lacks capability permission")
        if cap.get("adminOnly") and identity.role!="admin": deny("ADMIN_REQUIRED","admin role required")
        refs=list(ctx.get("evidenceRefs") or ([ctx["evidenceRef"]] if ctx.get("evidenceRef") else [])); task_id=ctx.get("taskId")
        if cap.get("requiresSourceEvidence"):
            q=self.store.evidence_quality(refs,task_id=task_id,allowed_kinds=cap.get("evidenceKinds"))
            if q<=0: deny("EVIDENCE_INVALID","verified task-bound source evidence required")
        if cap.get("requiresCredential"):
            consumer=cap.get("credentialConsumer",agent_id); cref=cap.get("credentialRef",capability_id)
            if not self.broker.check_scope(consumer,cref): deny("CREDENTIAL_DENIED","credential broker denied or credential unavailable")
        weight=COST_WEIGHTS[cap.get("costClass","high")]
        if weight:
            confirmation=ctx.get("confirmation") or {}
            if cap.get("costClass") in {"medium","high"}:
                expected=canonical_hash({"agent_id":agent_id,"capability_id":capability_id,"params":params,"task_id":task_id})
                if confirmation.get("binding")!=expected: deny("CONFIRMATION_REQUIRED","bound confirmation required")
            try: remaining=self.store.reserve_budget(task_id or "default",weight,self.default_budget)
            except ValueError as exc: deny("COST_DENIED",str(exc))
        else: remaining=None
        ph=canonical_hash(params); grant=self.store.create_grant(agent_id=agent_id,capability_id=capability_id,params_hash=ph,task_id=task_id)
        sig=hmac.new(self.grant_secret,json.dumps(grant,sort_keys=True,separators=(",",":")).encode(),hashlib.sha256).hexdigest()
        out={"approved":True,"executionGrant":{**grant,"signature":sig},"policyVersion":self.contract["version"],"policySha256":self.policy_sha256,"budgetRemaining":remaining}
        self.store.append_audit({"type":"capability_check","status":"APPROVED","agent_id":agent_id,"capability_id":capability_id,"task_id":task_id,"params_hash":ph,"grant_id":grant["grant_id"],"policy_sha256":self.policy_sha256})
        return out
    def consume_grant(self, identity, grant:dict, params:dict)->bool:
        unsigned={k:v for k,v in grant.items() if k!="signature"}; sig=grant.get("signature",""); expected=hmac.new(self.grant_secret,json.dumps(unsigned,sort_keys=True,separators=(",",":")).encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,expected): return False
        return self.store.consume_grant(unsigned["grant_id"],agent_id=identity.agent_id,capability_id=unsigned["capability_id"],params_hash=canonical_hash(params))
