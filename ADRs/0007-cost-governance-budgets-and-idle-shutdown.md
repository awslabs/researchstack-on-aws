---
status: proposed
date: 2026-04-07
subsystem: governance/budget, compute/ec2
related: [0001-service-catalog-simplification]
---

# 0007 - Cost Governance: Budget Alerts, Enforcement, and Idle Instance Shutdown

## Context

Research institutions transitioning to cloud face a fundamental cost model shift. On-premises HPC clusters are pre-paid capital expenses — researchers use as much as they want because capacity is already purchased. Cloud computing is pay-per-use, which means unmonitored usage can exceed grant budgets quickly. Two specific problems emerge:

1. **No spend visibility until the bill arrives.** Researchers and PIs don't have real-time awareness of how much their tagged resources are costing. By the time the monthly bill surfaces, overspend has already happened.

2. **Idle instances accumulate cost silently.** A researcher spins up an EC2 instance for analysis, finishes for the day, and forgets to stop it. The instance runs overnight, over the weekend, through a holiday — burning budget on zero utilization. This is the single most common source of cloud waste in research environments.

ResearchStack templates already enforce cost tracking tags (`CostCenter`, `Project`, `Owner`) on all resources, and the cost optimization guide documents manual strategies. But there's no automated mechanism to alert on spend thresholds or prevent idle waste.

## Decision

Implement a three-layer cost governance model: a standalone governance budget product, per-instance budgets embedded in EC2 templates, and idle instance shutdown.

### 1. Governance Budget Product (new template)

A new Service Catalog product (`templates/governance/budget-alert.yaml`) that creates an AWS Budget with SNS email notifications and optional account-wide enforcement.

**Design:**
- **Primary filter: CostCenter tag (required)** — this is the budget boundary. One budget per cost center aligns with how finance offices track grant spending.
- **Optional secondary filter: Project tag** — narrows the budget to a specific project within a cost center. Uses AND logic (resources must match both tags). Useful when a single grant funds multiple projects with separate sub-budgets.
- **No service dimension filter** — when money runs out, it runs out regardless of which service consumed it. Filtering by service adds a parameter for a niche use case.
- **Threshold notifications** — alerts at 50% (actual), 80% (actual), and 100% (forecasted) via SNS email.
- **Enforcement toggle** — deferred for v1. The governance budget is notification-only. Enforcement (IAM deny policy via `APPLY_IAM_POLICY` Budget Action) was designed and prototyped but removed because it requires the user to provide a `TargetIAMRoleName` — the IAM role to attach the deny policy to. This is straightforward for IT admins but confusing for researchers and PIs who don't know their IAM role names. Per-instance enforcement is handled by the EC2-embedded budget instead (which has the instance ID and doesn't require IAM role knowledge). Governance-level enforcement can be added back when there's demand.
  - **Important caveat (applies to EC2-embedded enforcement):** AWS Budgets evaluates cost data with up to 12-24 hour lag. This is not a real-time spending cap. The template description and parameter documentation must make this lag explicit.

**Why two options instead of four:** Considered offering separate PREVENT_NEW_LAUNCHES and STOP_RUNNING_INSTANCES options. The SSM-based stop action (`RUN_SSM_DOCUMENTS`) requires specific EC2 instance IDs at budget creation time, making it impractical for a governance budget where instances are provisioned later. The IAM deny approach (APPLY_IAM_POLICY) works without knowing instance IDs — it restricts the role, not the instances. Instance-level stopping is handled by the EC2-embedded budget and idle shutdown instead.

**Why a toggle instead of two products:** The budget definition (threshold, tags, period, notifications) is identical regardless of enforcement. Splitting into two products duplicates all budget configuration for no user benefit.

### 2. EC2-Embedded Budget (EC2 template enhancement)

Add optional per-instance budget tracking to all four EC2 templates with optional enforcement that stops *just that instance*.

**Design:**
- **Three new parameters per EC2 template:**
  - `EnableInstanceBudget` — `no` (default) / `notify` / `enforce`
  - `MonthlyInstanceBudgetUSD` — dollar amount (required when budget enabled)
  - `BudgetNotificationEmail` — email for alerts (required when budget enabled)
- **Budget filters:** CostCenter + Project tags (inherited from the instance's existing required parameters). Tracks all spend under those tags, not just EC2 — when money runs out, it runs out.
- **Notifications:** Same 50%/80%/100% thresholds as the governance budget.
- **Enforcement (when `enforce`):** Creates a Budget Action that stops *only this specific instance* (IAM role scoped to the instance ARN via `!Ref`). No account-wide blast radius. Does not prevent new launches (that's the governance budget's job).
- **Implementation lift:** ~25-30 lines of conditional CloudFormation per template. One `AWS::IAM::Role` (conditional), one Budget Action on the existing budget resource, one condition.
- **Launch role impact:** Existing EC2 launch roles already have `IAMFullAccess` (covers `iam:CreateRole`/`iam:PassRole` for the Budget Action execution role). No launch role changes needed.

**Why this exists alongside the governance budget:** A researcher who doesn't have an account-wide governance budget (common in single-account setups or early adoption) shouldn't be left with only notifications. The per-instance enforce option gives them a self-contained cost cap scoped to their instance. And unlike the governance budget's account-wide stop, this only affects the specific instance — no collateral damage to other projects sharing the account.

### 3. Idle Instance Shutdown (EC2 template enhancement)

Add CloudWatch-based idle detection to all four EC2 templates (general-purpose, compute-optimized, memory-optimized, GPU).

**Design:**
- **Two new parameters per template:**
  - `EnableIdleShutdown` (yes/no, default: yes)
  - `IdleMinutesBeforeShutdown` (default: 90, min: 30)
- **Implementation:** A `AWS::CloudWatch::Alarm` resource that monitors `CPUUtilization < 5%` for the configured duration, triggering the native CloudWatch EC2 stop action (`arn:aws:automate:{region}:ec2:stop`).
- **No Lambda or SSM required** — CloudWatch alarms have a built-in EC2 stop action, keeping the implementation lightweight (~30-40 lines of CloudFormation per template).
- **CPU threshold rationale:** 5% catches the "forgot to stop" scenario (instance truly idle) while giving headroom for background processes (SSM agent, OS services). The 90-minute default avoids false positives during brief pauses in interactive work.
- **Limitation acknowledged:** CPU utilization is not a perfect idle signal. I/O-bound workloads (large file transfers, database imports) may have low CPU while actively working. The parameter description documents this and advises disabling idle shutdown or increasing the duration for such workloads.
- **ParallelCluster excluded:** Compute nodes already auto-terminate via Slurm's `ScaledownIdletime`. The head node stays running intentionally as the scheduler.

### How the three layers complement each other

| Layer | Who provisions | Scope | Signal | Response time | Enforcement |
|-------|---------------|-------|--------|---------------|-------------|
| Governance budget | IT admin / PI / researcher | All tagged resources in account (macro) | Aggregate spend vs threshold | 12-24h lag | Notifications only (v1). IAM deny enforcement deferred — requires IAM role name knowledge. |
| EC2-embedded budget | Researcher | Per-instance spend (meso) | Tagged spend vs threshold | 12-24h lag | Stop this specific instance only |
| Idle shutdown | Automatic (default on) | Individual EC2 instance (micro) | CPU utilization | ~90 min (configurable) | Stop this specific instance |

- **Governance budget** catches the forest-level problem: total grant spend exceeding the budget.
- **EC2-embedded budget** catches the tree-level cost problem: a specific instance's project spend exceeding what the researcher intended.
- **Idle shutdown** catches the tree-level waste problem: an instance doing nothing but costing money.

A researcher could have all three active simultaneously with no conflicts — they operate on different signals and different scopes.

## Alternatives Considered

### Real-time cost enforcement via Lambda + Cost Explorer API
A Lambda function on a schedule (e.g., every 15 minutes) querying Cost Explorer and stopping instances when a threshold is hit. Rejected for v1: significantly more complex (Lambda, IAM, EventBridge schedule, Cost Explorer API calls with rate limits), and Cost Explorer itself has a data lag of several hours. The marginal improvement in response time over Budget Actions doesn't justify the complexity. Could revisit if institutions need tighter enforcement.

### Governance-level IAM deny enforcement deferred
Designed and prototyped `APPLY_IAM_POLICY` Budget Action that attaches a deny policy to a target IAM role when budget is exceeded. Removed from v1 because it requires the user to provide a `TargetIAMRoleName` parameter — straightforward for IT admins but confusing for researchers/PIs. Per-instance enforcement via the EC2-embedded budget covers the most important use case (stop my instance when I overspend) without requiring IAM knowledge. Can be added back as an "advanced" option if IT admins request it.

### Account-wide EC2 stop via Budget Actions
The SSM-based stop action (`RUN_SSM_DOCUMENTS` / `STOP_EC2_INSTANCES`) requires specific instance IDs at creation time per the `AWS::Budgets::BudgetsAction` `SsmActionDefinition` schema. This makes account-wide instance stopping impractical at the governance level where instances are provisioned later. Instance-level stopping is handled by the EC2-embedded budget (which has the instance ID at creation time) and idle shutdown.

### SCP-based enforcement
Budget Actions can apply an SCP to prevent launches at the Organizations level. Rejected: SCPs require management account access, which the Service Catalog hub account won't have. Also too broad — affects the entire account or OU regardless of cost center tags.

### EC2-embedded budget with no enforcement option
Considered making the EC2-embedded budget notify-only to keep templates simple. Rejected: if a researcher doesn't provision a governance budget (common in single-account setups), they'd have no enforcement mechanism at all. The per-instance stop action is ~25 lines of conditional CloudFormation and scopes enforcement to just that instance — low lift, high value.

### CloudWatch agent with custom idle metrics (logged-in users, process count)
More accurate idle detection than CPU alone. Rejected for v1: requires installing and configuring the CloudWatch agent in UserData, adds a dependency, and increases template complexity. CPU-based detection catches the 80% case (truly idle instances) with zero additional dependencies.

### Network-based idle detection (NetworkPacketsIn)
Catches whether anyone is connected, but background OS traffic (NTP, SSM agent heartbeats, DNS) creates a noisy baseline that varies by instance type and OS. Would require per-instance-type threshold tuning. Not worth the complexity for v1.

## Consequences

- New `templates/governance/` directory established as the home for governance-related products
- Governance budget product added to the research-computing portfolio in Service Catalog
- EC2 templates gain five new parameters each (2 idle shutdown + 3 budget) — all optional with sensible defaults
- Researchers get automated cost visibility without manual Cost Explorer usage
- IT admins get IAM-based enforcement on the governance budget; researchers get per-instance stop on the EC2-embedded budget — both opt-in
- Governance enforcement requires knowing the target IAM role name — documented clearly, but adds a setup step for IT admins
- The 12-24h lag on budget enforcement must be clearly documented to set expectations — this is not a real-time spending cap
- Idle shutdown default-on means existing EC2 deployments (if updated) would gain this behavior — acceptable since the 90-minute threshold is conservative and the toggle allows opt-out
- Cost allocation tags must be activated in the Billing console before budget tag filters work — documented in cost optimization guide
