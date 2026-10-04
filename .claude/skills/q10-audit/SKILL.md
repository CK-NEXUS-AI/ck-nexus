# Q10 Audit Skill

Purpose: perform Q10 evidence collection without confusing dependency/SAST/secret/configuration scans with Codex Security.

Flow:
1. Freeze target SHA/tree.
2. Run approved EG-1..EG-4 scanners.
3. Hash raw artifacts.
4. Normalize results.
5. Record EG-5 status separately.
6. Produce a verdict that preserves evidence-class boundaries.

Never mark Q10 FULL PASS from EG-1..EG-4 alone.
