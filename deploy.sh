#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#
# ResearchStack Deploy Helper
# Deploys CloudFormation templates from a config file.
# No dependencies beyond the AWS CLI and Python 3.
#
# Usage:
#   ./deploy.sh --config params/compute-general-ec2.json
#   ./deploy.sh --config params/compute-general-ec2.json --dry-run
#
# For interactive deployment, use the CloudFormation console:
#   https://console.aws.amazon.com/cloudformation/home#/stacks/create

set -euo pipefail

# ── Colours (disabled if not a terminal) ─────────────────────────────────────
if [[ -t 1 ]]; then
  BOLD="\033[1m" DIM="\033[2m" RESET="\033[0m"
  GREEN="\033[32m" CYAN="\033[36m" RED="\033[31m"
else
  BOLD="" DIM="" RESET="" GREEN="" CYAN="" RED=""
fi

info()  { echo -e "${CYAN}→${RESET} $*"; }
ok()    { echo -e "${GREEN}✓${RESET} $*"; }
err()   { echo -e "${RED}✗${RESET} $*" >&2; }

# ── Parse arguments ──────────────────────────────────────────────────────────
CONFIG_FILE=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config|-c)  CONFIG_FILE="$2"; shift 2 ;;
    --dry-run)    DRY_RUN=true; shift ;;
    --help|-h)
      echo "Usage: ./deploy.sh --config <params-file.json> [--dry-run]"
      echo ""
      echo "  --config, -c   Path to a parameter file (required)"
      echo "  --dry-run      Show the CloudFormation command without executing"
      echo ""
      echo "Example:"
      echo "  ./deploy.sh --config params/compute-general-ec2.json"
      echo ""
      echo "See params/README.md for available config files."
      exit 0
      ;;
    *) err "Unknown argument: $1. Run ./deploy.sh --help for usage."; exit 1 ;;
  esac
done

if [[ -z "$CONFIG_FILE" ]]; then
  err "Missing --config. Usage: ./deploy.sh --config params/<file>.json"
  echo ""
  echo "Available configs:"
  for f in "$(dirname "$0")"/params/*.json; do
    echo "  params/$(basename "$f")"
  done
  exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  err "Config file not found: ${CONFIG_FILE}"
  exit 1
fi

# ── Locate templates directory ───────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="${SCRIPT_DIR}/templates"

# ── Pre-flight checks ───────────────────────────────────────────────────────
if ! command -v aws &>/dev/null; then
  err "AWS CLI not found. Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  err "Python 3 not found (used to parse JSON config)."
  exit 1
fi

if [[ "$DRY_RUN" == false ]]; then
  if ! aws sts get-caller-identity &>/dev/null; then
    err "AWS credentials not configured. Run 'aws configure' or 'aws configure sso'."
    exit 1
  fi
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
  ok "AWS account ${ACCOUNT_ID} in ${REGION}"
else
  ACCOUNT_ID="(dry-run)"
  REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
  info "Dry run — no resources will be created"
fi

# ── Template catalogue ───────────────────────────────────────────────────────
# Resolved via Python to avoid bash 4+ associative array requirement
resolve_template() {
  python3 -c "
catalogue = {
    'vpc':       ('networking/research-vpc.yaml',          'IAM',      'Research VPC'),
    's3':        ('storage/s3-research-bucket.yaml',       '',         'S3 Research Bucket'),
    'efs':       ('storage/efs-shared-storage.yaml',       'IAM',      'Shared File Storage (EFS)'),
    's3files':   ('storage/s3-files.yaml',                 'IAM',      'S3 Files (Filesystem on S3)'),
    'fsx':       ('storage/fsx-lustre.yaml',               'IAM',      'FSx for Lustre'),
    'ec2-gp':    ('compute/ec2-general-purpose.yaml',      'IAM',      'EC2 General Purpose (M-series)'),
    'ec2-cpu':   ('compute/ec2-compute-optimized.yaml',    'IAM',      'EC2 Compute Optimized (C-series)'),
    'ec2-mem':   ('compute/ec2-memory-optimized.yaml',     'IAM',      'EC2 Memory Optimized (R-series)'),
    'ec2-gpu':   ('compute/ec2-accelerated-gpu.yaml',      'IAM',      'EC2 GPU (G-series)'),
    'ec2-spot':  ('compute/ec2-spot-fleet.yaml',           'IAM',      'EC2 Spot Fleet'),
    'pcluster':  ('compute/parallelcluster-hpc.yaml',      'IAM,AUTO', 'ParallelCluster (Slurm HPC)'),
    'sagemaker': ('ml/sagemaker-studio.yaml',              'IAM',      'SageMaker Studio'),
    'budget':    ('governance/budget-alert.yaml',           'IAM',      'Budget Alert'),
}
import sys
key = sys.argv[1]
if key not in catalogue:
    print(f'ERROR:Unknown template key: {key}. Valid: {\" \".join(catalogue.keys())}')
    sys.exit(1)
path, caps, name = catalogue[key]
print(f'PATH={path}')
print(f'CAPS={caps}')
print(f'NAME={name}')
" "$1"
}

# ── Read config ──────────────────────────────────────────────────────────────
read_config() {
  python3 -c "
import json, sys
with open('${CONFIG_FILE}') as f:
    config = json.load(f)

template = config.get('template', '')
stack_name = config.get('stack_name', '')
params = config.get('parameters', {})

print(f'TEMPLATE_KEY={template}')
print(f'STACK_NAME={stack_name}')
for k, v in params.items():
    if v is not None and str(v) != '':
        print(f'PARAM:{k}={v}')
"
}

TEMPLATE_KEY=""
STACK_NAME=""
PARAMS=()

while IFS= read -r line; do
  if [[ "$line" == TEMPLATE_KEY=* ]]; then
    TEMPLATE_KEY="${line#TEMPLATE_KEY=}"
  elif [[ "$line" == STACK_NAME=* ]]; then
    STACK_NAME="${line#STACK_NAME=}"
  elif [[ "$line" == PARAM:* ]]; then
    kv="${line#PARAM:}"
    key="${kv%%=*}"
    value="${kv#*=}"
    # Escape commas in values — AWS CLI shorthand syntax uses commas as delimiters
    escaped_value="${value//,/\\,}"
    PARAMS+=("ParameterKey=${key},ParameterValue=${escaped_value}")
  fi
done < <(read_config)

# ── Validate ─────────────────────────────────────────────────────────────────
if [[ -z "$TEMPLATE_KEY" ]]; then
  err "Config must have a 'template' field. See params/README.md for valid keys."
  exit 1
fi

TPATH="" TCAPS="" TNAME=""
while IFS= read -r line; do
  if [[ "$line" == ERROR:* ]]; then
    err "${line#ERROR:}"
    exit 1
  elif [[ "$line" == PATH=* ]]; then TPATH="${line#PATH=}"
  elif [[ "$line" == CAPS=* ]]; then TCAPS="${line#CAPS=}"
  elif [[ "$line" == NAME=* ]]; then TNAME="${line#NAME=}"
  fi
done < <(resolve_template "$TEMPLATE_KEY")

TEMPLATE_FILE="${TEMPLATES_DIR}/${TPATH}"
STACK_NAME="${STACK_NAME:-researchstack-${TEMPLATE_KEY}}"

if [[ ! -f "$TEMPLATE_FILE" ]]; then
  err "Template file not found: ${TEMPLATE_FILE}"
  exit 1
fi

# Check for REPLACE_ME values
for p in "${PARAMS[@]}"; do
  if [[ "$p" == *"REPLACE_ME"* ]]; then
    err "Config still has REPLACE_ME placeholders. Edit ${CONFIG_FILE} first."
    exit 1
  fi
done

# ── Build capabilities ───────────────────────────────────────────────────────
CAPS_FLAG=()
if [[ "$TCAPS" == *"IAM"* ]]; then
  CAPS_FLAG+=("CAPABILITY_IAM" "CAPABILITY_NAMED_IAM")
fi
if [[ "$TCAPS" == *"AUTO"* ]]; then
  CAPS_FLAG+=("CAPABILITY_AUTO_EXPAND")
fi

# ── Display summary ──────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Deployment Summary${RESET}"
echo "  Template:   ${TNAME}"
echo "  Stack name: ${STACK_NAME}"
echo "  Region:     ${REGION}"
echo "  Account:    ${ACCOUNT_ID}"
echo ""

CMD="aws cloudformation create-stack \\"
CMD+=$'\n'"  --stack-name ${STACK_NAME} \\"
CMD+=$'\n'"  --template-body file://${TEMPLATE_FILE}"
if [[ ${#CAPS_FLAG[@]} -gt 0 ]]; then
  CMD+=" \\"$'\n'"  --capabilities $(IFS=' '; echo "${CAPS_FLAG[*]}")"
fi
for p in "${PARAMS[@]}"; do
  display_p="$p"
  [[ "$p" == *"Password"* ]] && display_p="${p%%,*},ParameterValue=********"
  CMD+=" \\"$'\n'"  --parameters ${display_p}"
done

echo -e "${DIM}${CMD}${RESET}"
echo ""

if [[ "$DRY_RUN" == true ]]; then
  ok "Dry run complete — command shown above, nothing deployed."
  exit 0
fi

# ── Deploy ───────────────────────────────────────────────────────────────────
info "Creating stack ${STACK_NAME}..."

AWS_CMD=(aws cloudformation create-stack
  --stack-name "$STACK_NAME"
  --template-body "file://${TEMPLATE_FILE}"
)
[[ ${#CAPS_FLAG[@]} -gt 0 ]] && AWS_CMD+=(--capabilities "${CAPS_FLAG[@]}")
[[ ${#PARAMS[@]} -gt 0 ]] && AWS_CMD+=(--parameters "${PARAMS[@]}")

STACK_ID=$("${AWS_CMD[@]}" --query StackId --output text 2>&1) || {
  err "Deployment failed:"
  echo "$STACK_ID"
  exit 1
}

ok "Stack creation initiated: ${STACK_ID}"
echo ""
info "Monitor progress:"
echo "  aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].StackStatus'"
echo ""
info "View outputs after completion:"
echo "  aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs' --output table"
echo ""
