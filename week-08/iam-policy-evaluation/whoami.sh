#!/usr/bin/env bash
# assume the cs1660-w8-reader role and print the caller identity.
set -euo pipefail
cd "$(dirname "$0")"

ROLE_ARN="$(terraform output -raw role_arn)"

# assume the role: STS hands back temporary credentials (key, secret, session token).
# new roles can take a few seconds to become assumable (IAM is eventually consistent).
creds=""
for i in 1 2 3 4 5; do
  creds="$(aws sts assume-role --role-arn "$ROLE_ARN" --role-session-name cs1660-demo \
    --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text 2>/dev/null)" && break
  sleep 3
done
[[ -n "$creds" ]] || { echo "could not assume $ROLE_ARN" >&2; exit 1; }
read -r AK SK ST <<<"$creds"

echo "== you"
aws sts get-caller-identity --query Arn --output text

echo "== the role"
env -u AWS_PROFILE AWS_ACCESS_KEY_ID="$AK" AWS_SECRET_ACCESS_KEY="$SK" AWS_SESSION_TOKEN="$ST" \
  aws sts get-caller-identity --query Arn --output text
