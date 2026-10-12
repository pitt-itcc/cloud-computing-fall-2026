#!/usr/bin/env bash
# Run S3 calls AS the cs1660-w8-reader role, so AccessDenied messages are real.
# usage: ./reader.sh whoami | get KEY | put KEY | list | simulate
set -euo pipefail
cd "$(dirname "$0")"

BUCKET="$(terraform output -raw bucket)"
ROLE_ARN="$(terraform output -raw role_arn)"
CMD="${1:-whoami}"
KEY="${2:-}"

# Assume the role: STS hands back temporary credentials (key, secret, session token).
# New roles can take a few seconds to become assumable (IAM is eventually consistent).
as_role() {
  local creds="" i
  for i in 1 2 3 4 5; do
    creds="$(aws sts assume-role --role-arn "$ROLE_ARN" --role-session-name cs1660-demo \
      --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text 2>/dev/null)" && break
    sleep 3
  done
  [[ -n "$creds" ]] || { echo "could not assume $ROLE_ARN" >&2; exit 1; }
  read -r AK SK ST <<<"$creds"
  # env -u AWS_PROFILE: a named profile would win over these environment credentials.
  env -u AWS_PROFILE AWS_ACCESS_KEY_ID="$AK" AWS_SECRET_ACCESS_KEY="$SK" AWS_SESSION_TOKEN="$ST" "$@"
}

case "$CMD" in
  whoami)
    echo "== you";       aws sts get-caller-identity --query Arn --output text
    echo "== the role";  as_role aws sts get-caller-identity --query Arn --output text ;;
  list)
    as_role aws s3 ls "s3://$BUCKET" --recursive ;;
  get)
    # s3api, not "s3 cp": cp starts with HeadObject, whose 403 has no explanation.
    TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
    as_role aws s3api get-object --bucket "$BUCKET" --key "${KEY:?key required}" "$TMP" >/dev/null
    cat "$TMP"; echo "(allowed)" ;;
  put)
    TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
    echo "uploaded by the reader role" >"$TMP"
    as_role aws s3api put-object --bucket "$BUCKET" --key "${KEY:?key required}" --body "$TMP" >/dev/null
    echo "(allowed)" ;;
  simulate)
    # Ask IAM what it WOULD decide, without making the calls.
    aws iam simulate-principal-policy --policy-source-arn "$ROLE_ARN" \
      --action-names s3:GetObject s3:PutObject \
      --resource-arns "arn:aws:s3:::$BUCKET/public/hello.txt" "arn:aws:s3:::$BUCKET/secret/grades.csv" "arn:aws:s3:::$BUCKET/uploads/hw.txt" \
      --query 'EvaluationResults[].[EvalActionName,EvalResourceName,EvalDecision]' --output table ;;
  *)
    echo "usage: $0 whoami | get KEY | put KEY | list | simulate" >&2; exit 2 ;;
esac
