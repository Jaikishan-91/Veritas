# Agent Operating Manual

This file defines how AI coding agents operate in this repository. `CLAUDE.md` contains the governing principles; this file contains the execution procedure.

## Mandatory Lifecycle

Every non-trivial change follows:

PLAN → IMPLEMENT → TEST → REVIEW → DOCUMENT

Do not skip a pillar merely because the change appears small. For genuinely trivial changes, use judgment and record why a reduced workflow was appropriate.

---

# PILLAR 1 — PLAN / DISCOVER

Before modifying code:

1. Restate the objective internally in concrete engineering terms.
2. Inspect the repository structure.
3. Read `CLAUDE.md`.
4. Read the relevant project docs.
5. Locate the feature/module entry points.
6. Search for all important references.
7. Map the **blast surface**:
   - files;
   - modules;
   - APIs;
   - database/schema;
   - configuration;
   - background jobs;
   - external integrations;
   - tests;
   - documentation.
8. Read the relevant files, not merely search snippets.
9. Identify existing patterns and reusable utilities.
10. Identify constraints and risks.
11. Research external behavior when required.
12. Compare viable implementation approaches.
13. Select the simplest approach that satisfies the requirements.
14. Produce a concrete plan.

### Plan must include

- objective;
- current state;
- desired state;
- blast surface;
- files expected to change;
- files expected to be read but not changed;
- dependencies;
- implementation sequence;
- test strategy;
- documentation impact;
- risks;
- rollback/recovery considerations where relevant.

### Planning gate

No code changes until the plan is sufficiently concrete.

If important requirements are ambiguous, use `/grill-me`.

---

# PILLAR 2 — IMPLEMENT

1. Follow the approved plan.
2. Work in dependency order.
3. Preserve existing conventions.
4. Reuse existing code where appropriate.
5. Keep changes scoped.
6. Avoid opportunistic refactoring.
7. Do not silently change requirements.
8. Do not add unnecessary dependencies.
9. Keep security and error handling explicit.
10. Keep changes reviewable.

### Plan deviation

If implementation reveals a material flaw in the plan:

STOP → explain the discovery → update/re-run planning → continue only with the corrected plan.

Do not silently improvise a materially different architecture.

---

# PILLAR 3 — TEST / VERIFY

After implementation:

1. Determine what behavior changed.
2. Determine what could regress.
3. Add or update appropriate tests.
4. Run targeted tests first.
5. Run broader tests when appropriate.
6. Run lint/type checks/builds where applicable.
7. Exercise integration boundaries when applicable.
8. Verify failure and edge cases that matter.

Record:
- command;
- result;
- failures;
- environment limitations;
- unverified areas.

Never say "tests pass" unless the tests were actually executed.

---

# PILLAR 4 — REVIEW / HARDEN

Review the final diff against:

- original requirements;
- approved plan;
- architecture;
- security;
- data integrity;
- API compatibility;
- error handling;
- edge cases;
- performance;
- maintainability;
- duplication;
- dependency changes;
- observability;
- regression risk.

Fix material findings.

After fixes, re-run the affected tests.

---

# PILLAR 5 — DOCUMENT / CLOSE

Update only the documentation affected by the change.

The final record should answer:
- What changed?
- Why?
- Which files changed?
- What was tested?
- What was not tested?
- What limitations remain?
- Is follow-up work required?
