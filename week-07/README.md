# Week 7: Lambda


## lambda

A Python 3.14 function that estimates how many tokens a message will cost, packaged as a **container image** and stored in ECR. Its response also reports whether it was a cold start, which execution environment served it, and how many requests that environment has handled.

```
lambda/
  Dockerfile       FROM the AWS Lambda Python base image, copy the handler, CMD names it
  src/handler.py   the function
  main.tf          ECR repo + repo policy, execution role, log group, the function
  invoke.sh        one invocation, prints the REPORT line
  burst.sh         N concurrent invocations, counts execution environments
```

## Local testing

Build and run the container locally using the Lambda Runtime Interface Emulator (built into the base image):

```bash
cd week-07/lambda
docker build -t prompts .
docker run --rm -p 9000:8080 prompts
```

In another terminal, invoke the function:

```bash
curl -s http://localhost:9000/2015-03-31/functions/function/invocations -d '{"message": "hello"}' | jq -r .
```

This hits the same handler code that runs in Lambda — useful for testing changes before pushing to ECR.

## Getting started

A container-image function cannot be created until its image is in ECR, and Terraform does not build images. Follow the steps in [docs/ecr-build-tag-push.md](docs/ecr-build-tag-push.md) to create the repo, build, tag, and push the image, then apply the full Terraform config:

```bash
cd week-07/lambda
terraform init
terraform plan
terraform apply
```

## Try it

| Step | Command | Expect |
|---|---|---|
| Cold start | `./invoke.sh "how many tokens is this message"` | `cold_start: true`; the `REPORT` line includes `Init Duration` |
| Warm | run it again | same `env_id`, `invocations_in_env: 2`, no `Init Duration` |
| Timeout | `./invoke.sh "slow one" 5` | `Task timed out after 3.00 seconds` (3 s is the Lambda default) |
| Concurrency | `./burst.sh 10` | 10 requests, several `env_id`s: one environment serves one request at a time |
| Memory is CPU | `WORK=300000 ./invoke.sh x`, bump `memory_mb` in `variables.tf` and `terraform apply`, then repeat | `Duration` drops several times over |

New AWS accounts can start with a concurrency quota far below the usual 1,000. If `burst.sh` reports `TooManyRequestsException`, that quota is the reason, which is a good teaching moment rather than a broken demo.

## Clean up

```bash
cd week-07/lambda && terraform destroy
```

`force_delete` on the repository lets destroy remove it with the images still inside.
