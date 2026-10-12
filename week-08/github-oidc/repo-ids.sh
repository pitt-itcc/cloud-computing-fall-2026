#!/usr/bin/env bash
# Print the numeric IDs GitHub puts in the immutable OIDC sub claim.
# usage: ./repo-ids.sh OWNER/REPO      (private repos need GH_TOKEN set)
set -euo pipefail
REPO="${1:?usage: ./repo-ids.sh OWNER/REPO}"

AUTH=()
if [[ -n "${GH_TOKEN:-}" ]]; then AUTH=(-H "Authorization: Bearer $GH_TOKEN"); fi

curl -fsS ${AUTH[@]+"${AUTH[@]}"} -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO" | python3 -c '
import json, sys
r = json.load(sys.stdin)
owner, owner_id = r["owner"]["login"], r["owner"]["id"]
repo, repo_id = r["name"], r["id"]
print("github_owner    = \"%s\"" % owner)
print("github_owner_id = \"%s\"" % owner_id)
print("github_repo     = \"%s\"" % repo)
print("github_repo_id  = \"%s\"" % repo_id)
print()
print("sub claim: repo:%s@%s/%s@%s:ref:refs/heads/<branch>" % (owner, owner_id, repo, repo_id))
'
