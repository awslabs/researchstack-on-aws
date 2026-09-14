---
status: accepted
date: 2026-07-24
subsystem: templates/compute, docs
supersedes:
related: [0006-parallelcluster-template-fixes-and-fsx-integration]
---

# 0010 - EC2 Storage Is Decoupled and Opt-In (S3 Files Recommended)

## Context

The EC2 templates (general-purpose, compute-optimized, memory-optimized,
accelerated-gpu, spot-fleet) offer four ways to attach storage, all controlled
by parameters that default to blank:

- `SharedStorageBucketName` — creates a NEW S3 Files filesystem (backing bucket
  `{value}-{account}-{region}`), mounted at `/mnt/s3files`
- `S3FilesFileSystemId` — mounts an EXISTING S3 Files filesystem at `/mnt/s3files`
- `EfsFileSystemId` — mounts an EXISTING EFS filesystem at `/mnt/efs`
- `S3BucketName` — grants CLI read/write to an existing bucket (no mount)

With all four blank (the default), an instance is created with only its EBS root
volume — no shared storage. Storage is therefore **decoupled from compute and
opt-in**.

However, the documentation (templates/README, cost-optimization-guide, FAQ) and
some in-template code comments claimed the opposite: that EC2 templates
"auto-create S3 Files storage by default," with an `AutoCreateStorage` parameter
and a `none` opt-out. **That parameter does not exist in any template.** The
behavior is gated by `SharedStorageBucketName` being non-blank
(`AutoCreateS3Files: !Not [!Equals [!Ref SharedStorageBucketName, '']]`).

This drift appears to be the residue of an earlier design (an `AutoCreateStorage`
parameter defaulting to `s3-files`) that was refactored to the current opt-in
model without updating the docs or comments. The mismatch caused real confusion:
in live testing, the assistant, trusting the docs, told a user an instance would
have `/mnt/s3files` — but it wasn't there, because storage was never requested.
No ADR ever recorded a storage-default decision, so this is the first formal
record, not a reversal of a documented one.

## Decision

Keep storage **decoupled from compute and opt-in** (the current template
behavior), and make the documentation accurate and opinionated:

- An EC2 instance gets no shared storage unless the user sets one of the four
  parameters. Default remains EBS-root-only.
- **S3 Files is the recommended storage choice** for single-instance research
  workloads (~13x cheaper than EFS, POSIX mount). Docs recommend it explicitly
  and show the one-parameter path (`SharedStorageBucketName`), while being clear
  it is a deliberate choice, not an automatic default.
- Remove all references to the non-existent `AutoCreateStorage` parameter and the
  "auto-created by default" claim from docs and template comments.
- Document all four options, including the nuance that mounting an existing plain
  bucket requires deploying `s3-files.yaml` first (S3 Files needs its own
  filesystem in front of the bucket); `S3BucketName` gives CLI access, not a mount.

## Consequences

**Positive:**
- Docs match template behavior — no more phantom `/mnt/s3files` or ghost parameter.
- Decoupling avoids surprise: no S3 bucket + filesystem created for an instance
  the user only wanted for quick compute, and no orphaned storage to clean up.
- S3 Files remains the clearly-recommended path, so the cost story ("cheap POSIX
  storage in one step") is preserved without pretending it's automatic.

**Negative / trade-offs:**
- Slightly less "magical" than zero-config auto-mounted storage — the user must
  set one parameter to get a mount. Accepted for clarity and predictability.
- Non-trivial documentation surface to correct (templates/README, cost guide,
  FAQ, two template comment blocks). Done as part of this decision.

## Alternatives Considered

- **Restore auto-create-by-default** (make templates match the old docs): every
  EC2 auto-creates S3 Files unless opted out. Rejected for now — creating a
  bucket + filesystem for every instance is surprising, has cleanup and
  cost-tracking implications, and couples storage to compute. May be revisited if
  users find the opt-in step a friction point; the machinery still exists and
  only the default would change.
- **Leave docs as-is** — not viable; they describe a parameter that doesn't exist
  and behavior that doesn't happen, which actively misleads users and AI tooling.
