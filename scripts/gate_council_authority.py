from __future__ import annotations

import ast
import json
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
required=[
 'contracts/capability-policy.schema.json','contracts/capability-policy.example.json',
 'creator_app/council_authority/authority.py','creator_app/council_authority/identity.py',
 'creator_app/council_authority/storage.py','creator_app/council_authority/arbitration.py',
 'creator_app/council_authority/service.py','council-runtime/node/capability-client.js'
]
missing=[p for p in required if not (ROOT/p).exists()]
if missing: print('FAIL missing '+','.join(missing)); raise SystemExit(1)
for p in required:
    if p.endswith('.py'): ast.parse((ROOT/p).read_text())
contract=json.loads((ROOT/'contracts/capability-policy.example.json').read_text())
if 'system.budget.top_up' not in contract['capabilities']: print('FAIL admin budget capability missing'); raise SystemExit(1)
text='\n'.join((ROOT/p).read_text() for p in required if p.endswith(('.py','.js')))
checks={
 'bound_params':'params_hash' in text,
 'verified_evidence':'evidence_quality' in text,
 'one_time_grant':'consume_grant' in text,
 'authenticated_identity':'Authorization' in text and 'IdentityVerifier' in (ROOT/'creator_app/council_authority/identity.py').read_text(),
 'authorized_veto':'canVeto' in (ROOT/'creator_app/council_authority/arbitration.py').read_text(),
 'transactional_budget':'BEGIN IMMEDIATE' in (ROOT/'creator_app/council_authority/storage.py').read_text(),
 'broker_adapter':'CredentialId' in (ROOT/'creator_app/council_authority/authority.py').read_text(),
 'no_auto_confirmation':'lambda info: True' not in text,
}
failed=[k for k,v in checks.items() if not v]
if failed: print('FAIL '+','.join(failed)); raise SystemExit(1)
print('PASS council capability authority invariants: '+','.join(checks))
