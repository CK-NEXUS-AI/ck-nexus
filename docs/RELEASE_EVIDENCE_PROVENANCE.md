# Release Evidence Provenance

CK-NEXUS release evidence is fail-closed on both gate semantics and GitHub Actions artifact provenance.

The verifier `.github/release-tools/verify_release_evidence_provenance.py` checks the committed Q10-Q16 evidence against the GitHub Actions API and requires:

- the exact frozen release-subject manifest SHA-256;
- a concrete GitHub Actions `artifact_id`, `artifact_digest`, and `github_run_id`;
- an unexpired artifact whose server-side digest matches the committed evidence;
- artifact-to-run identity consistency;
- the expected verifier/candidate branch for each gate;
- a successful workflow conclusion for every PASS/PASS_CANDIDATE claim.

A future Q10 whole-gate PASS additionally requires open-source layered scan provenance fields: `open_source_security_scan=PASS`, `security_scan_run_id`, `security_report_sha256`, and `security_scan_completed_at`. Merely changing the dependency-audit status fields is insufficient.

This provenance layer does not replace the Q10 open-source layered security gate, the Q11 live provider gate, or the Q12 delegated cgroup-v2 gate. It only prevents committed evidence from being treated as trusted when its referenced GitHub Actions artifacts/runs cannot be independently reconciled.
