# CK-NEXUS Design-Partner Discovery Pack

**Date:** 2026-11-05
**Status:** Internal research instrument — no customer claims, prices, or commitments are approved by this document.

## Objective

Validate whether a specific buyer has a painful, budgeted problem that CK-NEXUS can solve better than existing workflow and agent platforms. The goal is evidence of willingness to pay and repeatability, not compliments about AI or feature requests.

## Target participant

Prioritize owners, CTOs, automation leads, or security/IT leads at Thai/regional MSPs and IT integrators that already deploy automation or AI for business customers. Include 2–3 direct enterprise IT buyers as a counter-sample so the team does not overfit to service partners.

## 30-minute interview

### Opening (2 minutes)

- We are researching how organizations deploy and govern AI-enabled workflows. This is not a sales demo.
- Ask permission to take notes. Do not request credentials, customer data, or confidential incident details.

### Current workflow and pain (10 minutes)

1. Walk me through the last AI or automation workflow you put into production.
2. Who owns the workflow after go-live? Who is allowed to change it?
3. What systems and data can it access?
4. What happens when an agent or workflow makes an uncertain or incorrect decision?
5. How do you approve high-impact actions today?
6. How do you investigate a run after a customer or auditor asks what happened?
7. What is the most expensive failure or delay you have experienced in this process?

### Buying process and existing alternatives (8 minutes)

8. Which products, scripts, and internal controls do you use today (e.g. n8n, Dify, Langflow, Sim, custom code, SIEM, IAM)?
9. What have you already tried to solve this problem? Why was it insufficient?
10. What security, data-residency, deployment, or licensing requirement blocks adoption?
11. Who owns the budget and who can veto a purchase?
12. What would cause this project to be funded in the next 90 days rather than deferred?

### Value and willingness to pay (7 minutes)

13. How many staff-hours per month go into deployment, manual review, incident handling, and evidence preparation?
14. What is the approximate cost of a failed or unauthorized action? Use a range if exact numbers are sensitive.
15. If a platform reduced this work and provided verifiable approval/evidence, what budget would it compete with?
16. Would you pay for a bounded pilot on one workflow? What must be included for that to be a real evaluation?
17. What would make you renew or expand after the pilot?

### Close (3 minutes)

- Ask for the next person who owns the operational or security problem.
- Ask permission to send a one-page pilot outline.
- Do not offer a discount or promise an unsupported feature during discovery.

## Evidence capture template

Record each interview separately. Distinguish direct quotes from interpretation.

| Field | Record |
|---|---|
| Organization / segment | |
| Participant role / buying authority | |
| Existing workflow and tools | |
| Painful event, frequency, severity | |
| Current workaround and cost | |
| Required deployment boundary | |
| Approval / identity / audit requirements | |
| Budget owner and buying trigger | |
| Current budget range (if volunteered) | |
| Willingness to pay for a pilot | Yes / No / Conditional + reason |
| Next step and permission | |
| Direct quote | Use quotation marks only for verbatim wording |
| Confidence | High / Medium / Low; explain why |

## Opportunity scoring

Score each dimension 0–5. Do not score from enthusiasm alone; cite the interview evidence.

| Dimension | 0 | 3 | 5 |
|---|---|---|---|
| Pain severity | No meaningful pain | Recurring workaround | Material cost, risk, or delay with a recent example |
| Frequency | Rare | Monthly | Weekly/daily |
| Budget | No owner or budget | Budget possible | Named owner and active budget |
| Urgency | No trigger | Exploring | Time-bound operational/security trigger |
| Product fit | Requires a different product | Some fit, major gaps | One workflow fits the current architecture |
| Repeatability | Unique custom project | Similar in a few firms | Same need across multiple target firms |
| Access to buyer | No path | Referral possible | Decision-maker engaged and willing to pilot |

**Interpretation:**
- 28–35: strong design-partner candidate; still require a paid pilot commitment.
- 20–27: continue discovery; identify the blocking assumption.
- 12–19: nurture only; do not build custom features yet.
- 0–11: disqualify or change segment/problem.

These thresholds are internal prioritization rules, not market benchmarks.

## Pilot offer template

### Scope

- One customer-controlled deployment, one named business workflow, one agreed integration path.
- One low/medium-risk action class first; sensitive or destructive actions remain human-approved or disabled.
- Customer supplies and controls its model/provider credentials and infrastructure.
- No shared multi-tenant data plane unless tenant isolation has passed dedicated verification.

### Deliverables

1. Deployment and operator handoff.
2. One working workflow with explicit policy and approval boundaries.
3. Run evidence export and a short audit walkthrough.
4. Baseline-versus-pilot metrics report.
5. Defect, limitation, and remediation register.
6. Exit plan: continue, expand, or remove the pilot and customer data.

### Success criteria — agree before installation

- Time to first successful run.
- Successful completion rate across an agreed test set.
- Human review and rework time.
- Approval latency and approval coverage.
- Unauthorized execution count (target zero).
- Evidence completeness and export success.
- Cost per successful run, including model and infrastructure costs.
- Operator effort to recover from a failed run.

### ROI model

Let:
- `H_before` = monthly staff-hours spent on the workflow before the pilot.
- `H_after` = monthly staff-hours after the pilot, including review and exception handling.
- `C_hour` = fully loaded hourly labor cost.
- `C_run` = monthly model, infrastructure, and third-party usage cost.
- `C_license` = monthly equivalent software license cost.
- `C_setup` = one-time implementation cost.

Then:

`Monthly gross benefit = (H_before - H_after) × C_hour`

`Monthly net benefit = Monthly gross benefit - C_run - C_license`

`Payback months = C_setup / Monthly net benefit`, only when Monthly net benefit is positive.

Also report non-financial risk reduction separately; do not convert avoided incidents into monetary savings unless the customer provides a defensible estimate.

## Pricing discovery rules

- Ask what budget the problem competes with before showing any CK-NEXUS price.
- Test a range only after the buyer confirms the problem, urgency, buyer, and procurement path.
- Separate annual software license, implementation, infrastructure/model consumption, and support.
- A verbal “sounds reasonable” is not willingness to pay. Stronger evidence is a paid pilot, procurement request, signed LOI with clear conditions, or a scheduled security review.
- Never discount in exchange for a testimonial that the customer has not yet earned through a successful pilot.

## Go / no-go after discovery

Proceed to a repeatable paid pilot only when:

- At least 10 interviews across at least 6 independent organizations are complete.
- At least 5 organizations independently describe substantially the same painful workflow.
- At least 3 qualified buyers agree to evaluate a scoped pilot.
- At least 2 buyers commit to a paid pilot or provide a procurement-backed path to one.
- The required workflow can be supported without weakening CK-NEXUS authority, security, or evidence gates.

If these conditions are not met, revise the segment or problem statement before adding broad features.
