---
status: accepted
date: 2026-07-24
subsystem: templates/networking, templates/compute, docs
supersedes:
related: [0010-ec2-storage-decoupled-opt-in]
---

# 0012 - Research VPC Defaults to 3 Availability Zones

## Context

The Research VPC template (`research-vpc.yaml`) has always had an
`AvailabilityZones` parameter (`MinValue: 2`, `MaxValue: 3`) that positionally
selects AZs via `!Select [n, !GetAZs '']`. Its default was **2**, so a
default deployment created public/private subnets in the region's first two AZs
only (e.g. `us-east-1a` and `us-east-1b`).

EC2 instances launch into the AZ of whichever subnet they are given — the
compute templates do not choose an AZ independently. GPU instance types (G- and
P-series) can have **per-AZ availability differences** of two distinct kinds:
(a) an instance type is simply **not offered** in a given AZ, and (b) a type is
offered but has a **transient capacity shortage** in one AZ while another AZ has
stock. Both surface at launch — case (a) as `InvalidRequest` ("not supported in
your requested Availability Zone"), case (b) as `InsufficientInstanceCapacity`
(ICE). A 2-AZ VPC that happens to align with neither an offering AZ nor a
currently-stocked AZ leaves the caller with nowhere to land.

This produced a real failure mode, observed during deployment testing: a
`g7e.2xlarge` deploy failed in `us-east-1a`, and AWS's own error message pointed
to another AZ as having capacity — but the 2-AZ VPC had **no subnet there**
(index 2 was never created). Recovery required manually adding a subnet or
redeploying the VPC with `AvailabilityZones=3`. This is the same class of "the
default quietly sets the user up to fail" problem addressed for storage in
ADR 0010.

**Scope of what this decision fixes — and what it does not.** Having subnets in
all of a region's AZs only helps when *some* AZ can serve the request. It
addresses case (a) fully (a not-offered AZ no longer blocks you if another AZ
offers the type and you have a subnet there) and the common *single-AZ*
transient-shortage case. It does **not** address a **region-wide** capacity
shortage, where every AZ is simultaneously out of stock. That was also observed
in the same testing: over a ~15-minute window, `g7e.2xlarge` on-demand capacity
ping-ponged and then dried up across all of `us-east-1`, Spot hit the same wall,
and Spot placement scores read 1/10 (worst) region-wide for both `g7e` and the
`g6e` fallback. No amount of AZ coverage wins that — the remedies are an
On-Demand Capacity Reservation / EC2 Capacity Block, a different instance
family, or a different region. Those remain the caller's decision and are out of
scope for this VPC-default change.

Two facts made a wider default cheap and safe:

1. **A third AZ is free until used.** The additional resources are two subnets,
   two route-table associations, and two outputs — all free. Critically, the
   template uses a **single NAT gateway** shared by one private route table, so
   a third AZ adds **no NAT cost** (NAT is the expensive VPC component). The
   `/16` is already carved into six `/24`s via `!Cidr [..., 6, 8]`, so a third
   AZ consumes pre-allocated CIDR with zero waste. Cost is incurred only when
   compute is launched into the third subnet.

2. **Every commercial AWS Region has at least 3 AZs** (per AWS Global
   Infrastructure documentation). `AvailabilityZones=3` and
   `!Select [2, !GetAZs '']` therefore resolve safely in every standard region.
   The template's existing `MaxValue: 3` prevents requesting a 4th that may not
   exist.

## Decision

**Change the `AvailabilityZones` default from 2 to 3. Keep the parameter.**

- The default now spans three AZs, giving scarce instance types (GPUs) three
  subnets — and therefore three AZs — to land in. This reduces the likelihood of
  a fresh deployment failing due to *single-AZ* misalignment (a not-offered AZ
  or a transient shortage in one AZ). It does not, and cannot, address a
  region-wide shortage (see Scope in Context).
- The parameter is retained (still accepts `2`) so a user with a constrained
  CIDR or a deliberate minimal-footprint need can opt down. The parameter was
  never the cause of the failure — the **default** was — so removing it would be
  more work (stripping the `Create3AZs` condition from ~7 resources/outputs) for
  a strictly less flexible result.

Supporting doc/verbiage changes (so the rationale is visible where users read
parameter descriptions):

- `research-vpc.yaml` `AvailabilityZones` description explains the capacity
  rationale and the opt-down path.
- `ec2-accelerated-gpu.yaml` `SubnetId` description adds a capacity hint at the
  decision point: the instance lands in the subnet's AZ; on ICE, try a subnet
  in a different AZ; the Research VPC spans 3 AZs by default.
- `templates/README.md` networking entry notes the 3-AZ default and why.

## Consequences

**Positive:**
- Fresh VPC deployments are more resilient to *single-AZ* placement failures (a
  type not offered in one AZ, or a transient shortage in one AZ), with no
  recurring cost and no region-portability risk. Region-wide shortages are not
  addressed (see Scope in Context).
- The fix targets the root cause (the default) via the same
  template-as-source-of-truth mechanism used elsewhere, keeping behavior
  consistent and self-documenting.
- Flexibility preserved: `AvailabilityZones=2` remains available.

**Negative / trade-offs:**
- Default VPCs contain one more (unused-until-populated) subnet set — marginally
  more stack resources and CIDR consumption. Judged negligible.
- The single shared NAT means egress from all three private subnets funnels
  through the AZ-1 NAT. A GPU instance in AZ-2/3 pulling heavily from the
  internet incurs cross-AZ NAT data-processing charges. Minor for the research
  workloads targeted; not a true multi-AZ-HA egress design (out of scope).
- Changing the default does not alter already-deployed 2-AZ VPCs; those would
  need a redeploy or a manually added subnet.

## Alternatives Considered

- **Keep default 2; nudge GPU users to set `AvailabilityZones=3` via guidance
  only.** Rejected as the primary fix: it leaves the failure-prone default in
  place and relies on the caller knowing to opt in. (The guidance/description
  improvements were kept as a complement, not a substitute.)

- **Remove the parameter and hardcode 3 AZs.** Rejected: more invasive (strip
  the `Create3AZs` condition across subnets, route associations, and outputs)
  and removes a legitimate escape hatch (constrained CIDR, minimal footprint),
  with no concrete requirement to forbid 2-AZ VPCs.

- **Capacity-aware ICE retry at deploy time** (auto-try another subnet on
  `InsufficientInstanceCapacity`). Deferred: it optimizes the wrong step —
  retrying across AZs cannot succeed during a region-wide shortage, which is a
  distinct failure from single-AZ misalignment. A more useful future direction
  is a **pre-deployment capacity check** (surface instance-type offerings per AZ
  and, where available, Spot placement scores) so a caller learns where a launch
  can succeed *before* a deploy-and-rollback cycle, and can be steered to a
  Capacity Reservation, another family, or another region. Recorded as a
  candidate; not adopted now (KISS).
