---
status: accepted
date: 2026-07-24
subsystem: templates/governance, docs
supersedes:
related: [0007-cost-governance-budgets-and-idle-shutdown]
---

# 0011 - Budget Alert Defaults to Account-Wide (CostCenter Optional)

## Context

The Budget Alert template (`budget-alert.yaml`, introduced in ADR 0007)
originally **required** a `CostCenter` value and always created a tag-filtered
budget (`CostFilters: user:CostCenter$<value>`). Tag-filtered budgets depend on
the `CostCenter` cost allocation tag being activated in the Billing console.

That activation is a hard prerequisite with three friction points, especially
for the researcher persona:

1. **It's a management-account action.** In an AWS Organizations setup, cost
   allocation tags can only be activated in the payer/management account and
   apply org-wide; member (spoke) accounts cannot activate them. A researcher in
   a spoke account cannot self-serve — they must file a request with central IT.
2. **~24-hour delay** after activation before the tag is usable in budgets.
3. **Silent-$0 failure:** a filtered budget created against a not-yet-activated
   tag tracks $0 indefinitely, giving false confidence that spend is being
   watched when it isn't.

So a researcher who simply wanted "warn me before I blow my grant" hit a wall
requiring someone else, a day's wait, and a silent failure mode. This runs
counter to the goal of making cost guardrails frictionless.

There is no way for the template (or a spoke-account tool) to detect tag
activation state: it lives in the management account and isn't queryable from
CloudFormation, nor reliably from a member account's credentials.

## Decision

Make `CostCenter` **optional** and default the budget to **account-wide** total
spend.

- `CostCenter` blank (new default) → `CostFilters` omitted → the budget tracks
  total account spend. No cost-allocation-tag activation, no management-account
  dependency, no 24h delay. Works immediately. This is the recommended path for
  the common one-account-per-lab/grant model.
- `CostCenter` set → tag-filtered budget (previous behavior), for per-grant
  tracking within a shared account. This still requires tag activation.
- `CostCenter` + `ProjectName` → narrowed to a project (previous behavior).

Because activation cannot be verified programmatically, surface the requirement
where it's unmissable rather than pretending to check it:

- A **conditional stack Output** (`TagActivationRequired`, present only when
  `CostCenter` is set) that plainly states the tag must be activated in the
  management account, takes ~24h, and that the budget tracks $0 until then.
- The `CostCenter` parameter description states the account-wide vs filtered
  tradeoff and the activation prerequisite.
- Docs (cost guide, FAQ) document both modes.

## Consequences

**Positive:**
- The common case (guardrail on a lab/grant account) now works with zero
  prerequisites and no management-account involvement.
- Removes a silent-failure trap for the default path (account-wide can't
  silently track $0 from a missing tag — there's no tag filter).
- Filtered budgets still available for FinOps/chargeback across shared accounts;
  the activation requirement is now stated loudly at deploy time instead of
  buried.

**Negative / trade-offs:**
- Account-wide budgets don't distinguish per-grant spend — institutions doing
  chargeback across a shared account still need the tag-filtered mode and its
  activation step.
- The silent-$0 risk still exists for the *filtered* mode; we mitigate with the
  Output warning and docs, but cannot eliminate it (no programmatic check).

## Alternatives Considered

- **Keep CostCenter required** (status quo): rejected — imposes a
  management-account prerequisite and silent-failure risk on the most common,
  simplest use case.
- **Check tag activation via `ce:ListCostAllocationTags` before deploying a
  filtered budget:** rejected. Cost allocation tag state is a management-account
  construct; a deployment running with a researcher's spoke-account credentials
  would query the wrong account, risking a confidently-wrong "not activated"
  signal — worse than no check. Doing it properly would require cross-account
  payer access, contradicting the least-privilege design. Recorded here so it
  isn't re-proposed.
