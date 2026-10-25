# Week 10 demo: DynamoDB operations

One on-demand table designed from four access patterns, plus a script that runs each
DynamoDB operation from the lecture.

| Access pattern | Operation |
|---|---|
| Get one order | `GetItem(customerId, orderId)` |
| A customer's orders, newest first | `Query(customerId)`, `ScanIndexForward=False` |
| A customer's orders in one month | `Query(customerId, begins_with(orderId, "2026-10"))` |
| Every order for a product | `Query` on the `by-product` GSI |

## Layout

```
load.py           seed the table with sample orders
demo.py           get, query, compare, and GSI demo commands
Dockerfile        container image for running the scripts
pyproject.toml    dependencies (boto3), managed with uv
uv.lock
terraform/        table, GSI, outputs
```

## Prerequisites

- AWS credentials for us-east-1, Terraform, Docker, and [uv](https://docs.astral.sh/uv/)

### AWS login (SSO)

```bash
aws sso login --profile sso
export AWS_PROFILE=sso
```

## Before class

```bash
cd terraform
terraform init
terraform apply                      # creates cs1660-orders-demo
cd ..
```

### Run with Python (uv)

```bash
uv run load.py                             # ~2,000 orders, 20 customers
uv run demo.py get c-7                     # GetItem: full primary key, 0.5 RCU
uv run demo.py query c-7                   # Query one partition, newest first
uv run demo.py query c-7 --month 2026-10   # sort key condition: begins_with
uv run demo.py compare c-7                 # Query vs Scan: same count, very different RCU
uv run demo.py product p-03                # GSI query
```

`uv run` installs boto3 from `pyproject.toml` on first use.

### Run with Docker

```bash
docker build -t ddb-demo .

# seed the table
docker run --rm \
  -v ~/.aws:/root/.aws -e AWS_PROFILE \
  ddb-demo load.py

# demo commands
docker run --rm -v ~/.aws:/root/.aws -e AWS_PROFILE ddb-demo demo.py get c-7
docker run --rm -v ~/.aws:/root/.aws -e AWS_PROFILE ddb-demo demo.py query c-7
docker run --rm -v ~/.aws:/root/.aws -e AWS_PROFILE ddb-demo demo.py query c-7 --month 2026-10
docker run --rm -v ~/.aws:/root/.aws -e AWS_PROFILE ddb-demo demo.py compare c-7
docker run --rm -v ~/.aws:/root/.aws -e AWS_PROFILE ddb-demo demo.py product p-03
```

The image packages the scripts and boto3 — no Python or uv on the host required.
Mounting `~/.aws` read-only gives the container your SSO session and config so
boto3 can resolve credentials the same way it does on the host.

## Afterwards

```bash
cd terraform && terraform destroy
```
