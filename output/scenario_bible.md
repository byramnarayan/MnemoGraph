# Scenario Bible — Aarohan Digital Networks Limited

## Company Overview

**Aarohan Digital Networks Limited** is a fictional integrated Indian telecom operator providing
mobile broadband (4G/5G), fiber, enterprise connectivity, and managed services across 22 licensed circles.
Headquartered in Mumbai, the company serves approximately 120 million subscribers and employs over 50,000 people
across six regional hubs in Mumbai, Delhi, Bengaluru, Hyderabad, Chennai, and Kolkata.

Founded in the late 1990s during India's telecom liberalisation, Aarohan has undergone multiple technology
generations and restructuring events. The dataset captures a 3-year operational window ending on the as-of date.

---

## Causal Storyline 1 — Outage Mis-Diagnosis

### Summary
A P1 outage in the Mumbai Metropolitan Circle is initially attributed to a BGP route flap caused by a
maintenance window ECMP policy change. An ineffective corrective action (ECMP rollback) is completed
and the incident is marked as resolved. Seven weeks later, a P2 recurrence strikes the same circle.
Investigation reveals the actual root cause was a Juniper firmware defect — the initial diagnosis was wrong.

### Key Entities
- **INC-0001**: P1 Mumbai Core Outage — cause initially `suspected` as BGP/ECMP issue
- **ACT-0001**: ECMP Rollback — `effectiveness_label = ineffective`, links to INC-0002 as recurrence
- **INC-0002**: P2 Repeat Outage — same incident type, started after INC-0001 resolved
- **DOC-0001**: PIR referencing both INC-0001 and INC-0002, documenting the mis-diagnosis

### Narrative Thread
The Focal Employee was the Network Architect on duty during INC-0001. Their initial diagnosis drove
the wrong corrective action. The confirmed root cause, identified via Juniper TAC 8 days after INC-0001,
forced an emergency firmware upgrade that actually prevented further recurrence.

---

## Causal Storyline 2 — Failed Technology Decision

### Summary
The Architecture Review Board approves NSA 5G architecture for Phase 2 of the core rollout.
The decision is later confirmed as negative: a hidden cost model error and insufficient cross-functional
review led to a technically inferior choice. The linked project is placed on hold with three milestones delayed.

### Key Entities
- **DEC-0003**: Technical decision, `outcome = negative`, with full `root_cause_analysis`
- **PROJ-0003**: 5G Core Network Upgrade Phase 2 — `status = on-hold`, `causal_decision_id = DEC-0003`
- **ACT-0004/0005/0006**: Three corrective actions: architecture review, revised CapEx model, updated decision framework
- **DOC-0005**: CAT document referencing DEC-0003 and ACT-0004/0005/0006

### Narrative Thread
The Focal Employee was the deciding executive (DEC-0003.deciding_emp_id). The decision was rushed to
meet a board presentation deadline. The RCA documented three compounding failures in the decision-making process.

---

## Causal Storyline 3 — Project Rescued by Corrective Action

### Summary
A P2 performance degradation incident caused by a capacity breach on the Bengaluru-Mumbai optical transport
segment triggers five corrective actions. The primary action (emergency capacity upgrade) is marked as
`prevented_recurrence`. This unblocks a previously on-hold optical transport expansion project which
subsequently completes ahead of schedule. The Focal Employee receives a promotion on the project completion date.

### Key Entities
- **INC-0004**: P2 Performance Degradation — confirmed capacity breach root cause
- **ACT-0007–0011**: Five corrective actions; ACT-0007 has `effectiveness_label = prevented_recurrence`
- **PROJ-0005**: Optical Transport Layer Expansion — rescued from on-hold, `status = completed`
- **Focal Employee**: Receives `RoleHistory` entry with `reason = promotion` on PROJ-0005 actual_end_date

---

## 10 Example Evaluation Questions

1. Which employee made the decision that placed the 5G Core Network Upgrade Phase 2 on hold?
2. What was the confirmed root cause of the P1 Mumbai outage, and how did it differ from the initial suspected cause?
3. Which corrective action was marked as ineffective after the P1 outage, and what recurrence incident did it fail to prevent?
4. How many milestones in PROJ-0003 have status `delayed`, and what decision caused this?
5. Which document provides a post-incident review covering both the P1 and P2 Mumbai outages?
6. What was the root cause analysis text for the NSA architecture decision?
7. Which employee received a promotion on the completion date of the optical transport expansion project?
8. What type of document was created to track corrective actions for the failed NSA architecture decision?
9. List all follow-up actions linked to the P2 performance degradation incident, ordered by due date.
10. What was the confirmed cause of INC-0004, and which project did the resolution unblock?
