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
tests/                pytest for the handler: uv run pytest
pyproject.toml        dependencies, managed with uv (uv add <pkg>, then uv lock)
uv.lock
Dockerfile            multi-stage: uv installs deps into the Lambda task root, then app code is copied in
cognito.tf            user pool, login domain, app client
lambda.tf             ECR repo + pull policy, image build/push, the function
api.tf                REST API, Cognito authorizer, /public and /me
login.py              authorization code + PKCE login, standard library only
```

## Prerequisites

Docker running, the AWS CLI logged in, Terraform, and uv.

`terraform apply` builds and pushes the image with your local Docker, so set the architecture to match your laptop: `arm64` (default, Apple Silicon) or `-var architecture=x86_64` (Intel/AMD). The image tag is a hash of `app/`, `Dockerfile`, `pyproject.toml`, and `uv.lock`, so editing the handler and re-running `terraform apply` rebuilds, pushes, and redeploys.

## Before class

```bash
uv run pytest                        # handler tests, no AWS needed
terraform init
terraform apply                      # a few minutes the first time (image build + push)
terraform output -raw signup_url     # open it, create a user, confirm the emailed code
```

Pre-creating the user saves a few minutes and avoids waiting on the confirmation email live. (The browser lands on a `localhost` page that won't load after sign-up. That's expected.)

## In class

```bash
# 1. Public route works for anyone
API_URL=$(terraform output -raw api_url)
curl "$API_URL/public"

# 2. Protected route rejects you
curl -i "$API_URL/me"                # 401 {"message":"Unauthorized"}

# 3. Log in (steps 1-6 on the whiteboard)
python3 login.py                     # opens the Cognito login page, catches the redirect,
                                     # trades the code for tokens, prints the ID token

# 4. Call the API with the token (steps 7-8)
source .tokens
curl -H "Authorization: $ID_TOKEN" "$API_URL/me"

# 5. Tamper with the token: change one character in the payload and watch it fail
BAD=$(python3 -c 'import os; t=os.environ["ID_TOKEN"]; i=t.index(".")+20; print(t[:i] + ("A" if t[i] != "A" else "B") + t[i+1:])')
curl -i -H "Authorization: $BAD" "$API_URL/me"               # 401
```

Things worth showing along the way:

- Paste `$ID_TOKEN` into [jwt.io](https://jwt.io) and compare `iss`, `aud`, `sub`, `exp` with the GitHub token from Block A.
- Open `terraform output -raw discovery_url` and then `jwks_url` in a browser: that's where API Gateway gets the public keys.
- In `terraform/api.tf`, the only difference between the two routes is `authorization = "NONE"` vs `"COGNITO_USER_POOLS"`.

## Notes

- The token goes in the header **raw**, with no `Bearer ` prefix. With no OAuth scopes on the method, the Cognito authorizer expects the **ID token**. Sending `$ACCESS_TOKEN` gets a 401 until you add `authorization_scopes` to the method.
- If the login page is unreachable or the browser can't open, a CLI fallback that skips the browser flow:

  ```bash
  aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH \
    --client-id "$(terraform output -raw client_id)" \
    --auth-parameters USERNAME=you@pitt.edu,PASSWORD='YourPassword1' \
    --query AuthenticationResult.IdToken --output text
  ```

- Callback URL errors (`redirect_mismatch`) mean the URL differs from `callback_url` by even one character.
- `docker push` fails with `no basic auth credentials`: the ECR login expired; re-run `terraform apply`.
- `image manifest media type not supported` on the Lambda: the image was pushed without `--provenance=false`. The Terraform build step sets it; a manual `docker buildx build` needs it too.
- Cost: pennies at class scale. Cognito, API Gateway, and Lambda are within the free tier for a demo; ECR storage for one small image is a few cents a month until `terraform destroy`.

## Teardown

```bash
terraform destroy
```
