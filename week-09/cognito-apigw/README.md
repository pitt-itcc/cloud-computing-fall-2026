# Week 9 Demo: Cognito + API Gateway

A Cognito user pool in front of a REST API. One Lambda serves two routes:

| Route | Authorizer | Without a token | With a valid ID token |
|---|---|---|---|
| `GET /public` | none | 200 | 200 |
| `GET /me` | Cognito | **401**, Lambda never runs | 200, echoes your claims |

The Lambda has no token-checking code. API Gateway verifies the token (signature, issuer, expiry) against the user pool before the function runs, then passes the claims in the event.

`login.py` walks the same login flow as the whiteboard (see `../oauth2-oidc/README.md`) and prints each numbered step.

## Layout

```
app/handler.py        the Lambda (stdlib only), packaged as a container image like week 7
pyproject.toml        dependencies, managed with uv (uv add <pkg>, then uv lock)
uv.lock
Dockerfile            multi-stage: uv installs deps into the Lambda task root, then app code is copied in
cognito.tf            user pool, login domain, app client
lambda.tf             IAM role, log group, the function (ECR repo is created before Terraform)
api.tf                REST API, Cognito authorizer, /public and /me
login.py              authorization code + PKCE login, standard library only
```

## Prerequisites

- Docker running, the AWS CLI logged in, Terraform, and uv
- an ECR repo named `cognito-demo` with the image already pushed (see [week 7 docs](../../week-07/docs/ecr-build-tag-push.md) if you need a refresher)
- `uv run pytest` passes

```bash
cd terraform
terraform init
terraform apply -var "image_tag=$TAG"   # TAG = whatever you pushed to ECR
```

Set the architecture to match your laptop: `-var architecture=x86_64` (Intel/AMD) or `arm64` (Apple Silicon, the default in `variables.tf`). Pre-creating the user saves a few minutes and avoids waiting on the confirmation email live. (The browser lands on a `localhost` page that won't load after sign-up. That's expected.)

## In class

```bash
# load terraform outputs as env vars (login.py reads these automatically)
export API_URL=$(terraform -chdir=terraform output -raw api_url)
export COGNITO_DOMAIN=$(terraform -chdir=terraform output -raw cognito_domain)
export CLIENT_ID=$(terraform -chdir=terraform output -raw client_id)

# 1. public route works for anyone
curl "$API_URL/public"

# 2. protected route rejects you
curl -i "$API_URL/me"                # 401 {"message":"Unauthorized"}

# 3. log in (opens the browser, catches the redirect, exchanges the code for tokens)
python3 login.py

# 4. call the API with the token (steps 7-8 on the whiteboard)
source .tokens
curl -H "Authorization: $ID_TOKEN" "$API_URL/me"

# 5. tamper with the token: change one character in the payload and watch it fail
BAD=$(python3 -c 'import os; t=os.environ["ID_TOKEN"]; i=t.index(".")+20; print(t[:i] + ("A" if t[i] != "A" else "B") + t[i+1:])')
curl -i -H "Authorization: $BAD" "$API_URL/me"               # 401
```

## Teardown

```bash
cd terraform
terraform destroy
aws ecr delete-repository --repository-name cognito-demo --force --region us-east-1
```
