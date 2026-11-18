# Week 11 Demo: One Upload, Two Workers, One Poison Message

```
S3 (uploads/) ──► SNS topic ──► thumbs-queue ──► thumbnail Lambda ──► S3 (thumbs/)
                            └─► meta-queue   ──► metadata Lambda  ──► logs
                 each queue has its own DLQ (maxReceiveCount = 3)

S3 ──► EventBridge default bus ──► rule: uploads/ AND size > 1 MB ──► log group
```

| Path | What it is |
| --- | --- |
| `Dockerfile` | Lambda Python 3.12 base image; both handlers, one image |
| `src/workers.py` | Both Lambda handlers (thumbnail and metadata) in one file, no dependencies |
| `terraform/` | Bucket, SNS topic, 2 queues + 2 DLQs, 2 Lambdas, EventBridge rule |
| `tests/` | Handler tests with moto-mocked S3; no AWS needed |

The workers ship as a container image pushed to ECR. Both Lambdas share the
same image; each one overrides the `CMD` via `image_config.command` to select
its handler. You build and push the image manually before `terraform apply`.

## Before class

Create the ECR repo and push the image:

```bash
export AWS_REGION=us-east-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REPO_NAME=eda-demo-workers
export IMAGE_URI=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest

aws ecr create-repository --repository-name $REPO_NAME
aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
docker build -t $IMAGE_URI .
docker push $IMAGE_URI
```

Then deploy the infrastructure:

```bash
cd terraform
terraform init
terraform apply -var "image_uri=$IMAGE_URI"

export BUCKET=$(terraform output -raw bucket)
export THUMBS_LOG=$(terraform output -json log_groups | jq -r .thumbs)
export META_LOG=$(terraform output -json log_groups | jq -r .meta)
export BIG_LOG=$(terraform output -json log_groups | jq -r .large_uploads)
export THUMBS_DLQ=$(terraform output -json dlq_urls | jq -r .thumbs)
export THUMBS_DLQ_ARN=$(terraform output -json dlq_arns | jq -r .thumbs)
```

Open two extra terminals with the same exports and start the log tails:

```bash
aws logs tail "$THUMBS_LOG" --follow --format short   # terminal 2
aws logs tail "$META_LOG"   --follow --format short   # terminal 3
```

Have a test image ready (`cat.jpg`) and make the files for later steps:

```bash
echo "definitely not an image" > bad.txt
head -c 2000000 /dev/urandom > big.jpg   # 2 MB, for the EventBridge rule
```

## In class

### 1. Show what Terraform built (1 min)
In the console: the SNS topic's two SQS subscriptions, and the bucket's
**Properties → Event notifications** (one SNS rule on `uploads/`, EventBridge: On).

### 2. Fan-out (2 min)

```bash
aws s3 cp cat.jpg "s3://$BUCKET/uploads/"
```

- The command returns immediately; the work happens afterward.
- Both tails print the same key within a few seconds. Neither Lambda knows the other exists.
- `aws s3 ls "s3://$BUCKET/thumbs/"` shows the thumbnail. It went to `thumbs/`, not
  `uploads/`, so it doesn't re-trigger the pipeline (slide 9's loop warning).

### 3. Poison message (3 min, mostly waiting)

```bash
aws s3 cp bad.txt "s3://$BUCKET/uploads/"
```

- Metadata tail: `OK`. Thumbnail tail: `FAILED ... receiveCount: 1`.
- The message is invisible for the 30 s visibility timeout (6x the 5 s function
  timeout), then comes back: `receiveCount: 2`, then `3`.
- Fill the wait: this is why consumers must be idempotent, and why a DLQ exists.
- After the third failure SQS moves it to the DLQ (expect about 1.5 to 2 minutes total):

```bash
aws sqs get-queue-attributes --queue-url "$THUMBS_DLQ" \
  --attribute-names ApproximateNumberOfMessages
```

- Point out that the metadata worker was never affected: separate queues, separate failures.

### 4. Redrive (1 min)
"We fixed the bug, replay the failures." Console: thumbs DLQ → **Start DLQ redrive**, or:

```bash
aws sqs start-message-move-task --source-arn "$THUMBS_DLQ_ARN"
```

It moves back to `thumbs-queue` and fails again, since nothing was actually fixed. That's
expected, and it's a good moment to ask what *should* happen to a file that can never succeed.

### 5. Optional: EventBridge rule (1 min)

```bash
aws s3 cp big.jpg "s3://$BUCKET/uploads/"
aws logs tail "$BIG_LOG" --since 5m --format short
```

`cat.jpg` never showed up here; `big.jpg` (over 1 MB) did. Same S3 event, matched by
content. Show the rule's event pattern in the console next to slide 11.

## After class

```bash
terraform destroy -var "image_uri=$IMAGE_URI"
aws ecr delete-repository --repository-name $REPO_NAME --force
```

## Running the tests locally

```bash
uv run --with boto3 --with "moto[s3]" --with pytest pytest tests/
```

## Knobs (`terraform/variables.tf`)

| Variable | Default | Effect |
| --- | --- | --- |
| `image_uri` | *(required)* | ECR image URI for the worker Lambda |
| `function_timeout` | 5 | Lambda timeout; queue visibility timeout = 6x this |
| `max_receive_count` | 3 | Failed receives before the DLQ |
| `large_upload_bytes` | 1000000 | EventBridge size threshold |

Lower `function_timeout` to 2 for a faster DLQ demo (12 s visibility timeout).
