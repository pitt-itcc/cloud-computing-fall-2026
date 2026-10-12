# IAM Policy Evaluation Demo

This demo creates an S3 bucket and a restricted IAM role to show the three outcomes of an IAM policy evaluation: **allow**, **explicit deny**, and **implicit deny**.

## What gets created

- an S3 bucket with two objects: `public/hello.txt` and `secret/grades.csv`
- a role (`cs1660-w8-reader`) with a policy that:
  - **allows** `s3:ListBucket` on the bucket
  - **allows** `s3:GetObject` on all objects (`/*`)
  - **explicitly denies** `s3:GetObject` on `secret/*`
  - says nothing about `s3:PutObject` (implicit deny)

## Setup

```bash
cd week-08/iam-policy-evaluation
terraform init && terraform apply
```

## Using whoami.sh

`whoami.sh` assumes the `cs1660-w8-reader` role and prints both your admin identity and the assumed role identity:

```bash
./whoami.sh
```

```
== you
arn:aws:iam::123456789012:user/your-admin-user
== the role
arn:aws:sts::123456789012:assumed-role/cs1660-w8-reader/cs1660-demo
```

## Testing the policy

### Configure a profile to assume the role

Add this to `~/.aws/config`:

```ini
[profile cs1660-demo]
role_arn = <ROLE_ARN from terraform output>
source_profile = default
```

Or as a one-liner:

```bash
aws configure set profile.cs1660-demo.role_arn $(terraform output -raw role_arn)
aws configure set profile.cs1660-demo.source_profile default
```

Set the bucket name:

```bash
export BUCKET=$(terraform output -raw bucket)
```

### Run the commands as the restricted role

| Command | Expect | Why |
|---|---|---|
| `aws --profile cs1660-demo s3api get-object --bucket $BUCKET --key public/hello.txt hello.txt` | allowed | `ReadEveryObject` allows `s3:GetObject` on `/*` |
| `aws --profile cs1660-demo s3api get-object --bucket $BUCKET --key secret/grades.csv grades.csv` | explicit deny | `ButNeverTheGrades` denies `s3:GetObject` on `secret/*` — beats the allow |
| `aws --profile cs1660-demo s3api put-object --bucket $BUCKET --key uploads/hw.txt --body hello.txt` | implicit deny | nothing in the policy mentions `s3:PutObject` |

### Fix the implicit deny

```bash
terraform apply -var allow_uploads=true
```

Try `put-object` again — it works now. But `put-object` on `secret/*` still fails because the explicit deny always wins.

## Key takeaways

- **explicit deny > allow > implicit deny** — that's the evaluation order
- `s3:ListBucket` targets the **bucket** ARN, `s3:GetObject` targets **objects** (`bucket/*`) — mixing these up is a common mistake
- the trust policy's `arn:aws:iam::<account>:root` means "any identity in this account", not the root user
