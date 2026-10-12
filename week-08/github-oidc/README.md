# GitHub OIDC --> AWS (Keyless CI/CD)

This lab replaces long-lived AWS access keys with short-lived credentials that GitHub Actions obtains automatically via OpenID Connect. No secrets to rotate, no keys to leak.

## How it works

1. GitHub Actions mints a signed OIDC token for every workflow run
2. The workflow exchanges that token for temporary AWS credentials via `sts:AssumeRoleWithWebIdentity`
3. AWS validates the token against the OIDC provider and checks the trust policy conditions (audience, subject) before issuing credentials

## Step 1: Create the OIDC identity provider (Console)

> One per account — if your account already has `token.actions.githubusercontent.com`, skip this step.

1. Open **IAM → Identity providers → Add provider**
2. Choose **OpenID Connect**
3. **Provider URL:** `https://token.actions.githubusercontent.com`
4. **Audience:** `sts.amazonaws.com`
5. Click **Add provider** — AWS auto-fetches the thumbprint

Docs: [Creating an OIDC identity provider](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)

## Step 2: Create the IAM role and trust policy

Create a role with a trust policy that only lets a specific repo and branch assume it:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:pitt-itcc@328444000/<REPO NAME>@<REPO ID>:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

Attach a permission policy to control what the role can actually do (e.g. `s3:ListAllMyBuckets`).

The org ID for `pitt-itcc` is **328444000**, this is the same for all repos in the org. To get your repo ID:

```bash
curl -s https://api.github.com/repos/pitt-itcc/<YOUR_REPO> | jq '.id'
```

```bash
gh api repos/pitt-itcc/<YOUR_REPO> --jq '.id'
```

## Step 3 — Add the workflow

[workflow example](../../.github/workflows/whoami.yml)

```yaml
permissions:
  id-token: write   # required — lets the job request an OIDC token
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v6
    with:
      role-to-assume: ${{ vars.AWS_ROLE_ARN }}
      aws-region: us-east-1
```

Set the repository variable `AWS_ROLE_ARN` under **Settings → Secrets and variables → Actions → Variables**. It is not a secret — the trust policy, not the ARN, is what protects it.

Docs: [configure-aws-credentials action](https://github.com/aws-actions/configure-aws-credentials)
