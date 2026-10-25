# Week 10 demo: S3 operations

Create a bucket, put objects, get them back, list, and clean up — all from the CLI
using boto3.

## Prerequisites

- AWS credentials for us-east-1 and [uv](https://docs.astral.sh/uv/)

### AWS login (SSO)

```bash
aws sso login --profile sso
export AWS_PROFILE=sso
```

## Before class

```bash
cd terraform
terraform init
terraform apply       # creates cs1660-s3-demo-<account-id> with a 7-day lifecycle rule
cd ..
```

## Demo

```bash
uv run demo.py put hello.txt "hello from cs1660"       # PutObject
uv run demo.py put data/grades.json '{"midterm": 92}'   # keys can have path prefixes
uv run demo.py get hello.txt                             # GetObject
uv run demo.py list                                      # ListObjectsV2
uv run demo.py list --prefix data/                       # filter by prefix (not a folder)
uv run demo.py delete hello.txt                          # DeleteObject
uv run demo.py list                                      # confirm it's gone
```

### What to point at

- **prefix is not a folder**: `data/grades.json` is a flat key, not a file in a directory.
  `--prefix data/` filters on the key string, not a filesystem path.
- **public access block**: the create-bucket command locks down all four public access
  settings immediately — show this in the console under the bucket's Permissions tab.

## Teardown

```bash
cd terraform && terraform destroy
```

The bucket name defaults to `cs1660-s3-demo-<account-id>`. Override with `BUCKET_NAME`.
