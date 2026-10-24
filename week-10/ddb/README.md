# Week 10 demo: DynamoDB operations

One on-demand table designed from four access patterns, plus a script that runs each
DynamoDB operation from the lecture.

| Access pattern | Operation |
|---|---|
| Get one order | `GetItem(customerId, orderId)` |
| A customer's orders, newest first | `Query(customerId)`, `ScanIndexForward=False` |
| A customer's orders in one month | `Query(customerId, begins_with(orderId, "2026-10"))` |
| Every order for a product | `Query` on the `by-product` GSI |

## Before class

```bash
cd terraform
terraform init
terraform apply                      # creates cs1660-orders-demo
cd ..
uv run demo.py seed                  # ~2,000 orders, 20 customers, takes under a minute
```

Prerequisites: AWS credentials for us-east-1, Terraform, and [uv](https://docs.astral.sh/uv/).
`uv run` installs boto3 from `pyproject.toml` on first use.

## In class

```bash
uv run demo.py get c-7                     # GetItem: full primary key, 0.5 RCU
uv run demo.py query c-7                   # Query one partition, newest first
uv run demo.py query c-7 --month 2026-10   # sort key condition: begins_with
uv run demo.py compare c-7                 # Query vs Scan: same count, very different RCU
uv run demo.py page c-7 --limit 5          # follow LastEvaluatedKey page by page
uv run demo.py create                      # attribute_not_exists vs silent overwrite
uv run demo.py lock                        # optimistic locking: stale version is rejected
uv run demo.py product p-03                # GSI query (access pattern 4)
uv run demo.py floats                      # float TypeError and Decimal json.dumps bugs
```

Every command prints what it sent and the consumed capacity, so you can project the
terminal and talk over the output. While it runs, keep the table's **Explore items**
page open in the console to show the same items.

### What to point at

- **compare**: the Query reports `scanned` equal to `count`; the Scan reports
  `scanned=2000` for the same answer, and its RCU is roughly 20x the Query's
  (one customer out of 20). FilterExpression shrank the response, not the bill.
- **page**: each page's `LastEvaluatedKey` is just the key of its last item.
  That dict is what an API would return to the client as an opaque `next` token.
- **create**: step 3 succeeding silently and dropping `giftNote` is the point.
- **lock**: the final item shows client A's total and version 2. Client B got
  `ConditionalCheckFailedException` instead of erasing A's change.
- **product**: GSI reads are eventually consistent only; `--consistent` isn't offered there.

The `create`, `lock`, and `floats` steps use fixed keys and clean up or overwrite their
own items, so you can rerun any step.

## Afterwards

```bash
cd terraform && terraform destroy
```

Or leave it up for office hours. On-demand billing means an idle table costs only storage,
which this one barely uses.

Set `TABLE_NAME` if you changed the table name in Terraform:
`TABLE_NAME=$(terraform -chdir=terraform output -raw table_name) uv run demo.py get c-7`.
