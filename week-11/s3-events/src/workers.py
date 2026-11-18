"""Two independent workers fed by the same S3 upload.

S3 -> SNS -> (thumbs-queue, meta-queue) -> one Lambda per queue.

Both functions live in this one file; Terraform points each Lambda at a
different handler via image_config.command (workers.thumbnail_handler /
workers.metadata_handler). Ships as a container image on the Lambda
Python 3.12 base image.
"""

import json
import os
from urllib.parse import unquote_plus

import boto3

s3 = boto3.client("s3")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
THUMBS_PREFIX = os.environ.get("THUMBS_PREFIX", "thumbs/")


def s3_objects(record):
    """Yield (bucket, key, size) for every S3 object in one SQS record.

    The subscription uses raw message delivery, so the SQS body IS the S3
    event. Without raw delivery you would unwrap one more layer:
    json.loads(json.loads(body)["Message"]).
    """
    event = json.loads(record["body"])

    # S3 sends a one-time s3:TestEvent when the notification is configured.
    if event.get("Event") == "s3:TestEvent":
        print(json.dumps({"skipped": "s3:TestEvent"}))
        return

    for r in event.get("Records", []):
        yield (
            r["s3"]["bucket"]["name"],
            unquote_plus(r["s3"]["object"]["key"]),  # "my+cat.jpg" -> "my cat.jpg"
            r["s3"]["object"].get("size", 0),
        )


def run_batch(event, work):
    """Process an SQS batch, reporting only the messages that failed.

    Requires function_response_types = ["ReportBatchItemFailures"] on the
    event source mapping. Failed messages go back to the queue; after
    maxReceiveCount attempts SQS moves them to the dead-letter queue.
    """
    failures = []
    for record in event["Records"]:
        receive_count = record["attributes"].get("ApproximateReceiveCount", "?")
        try:
            for bucket, key, size in s3_objects(record):
                work(bucket, key, size, receive_count)
        except Exception as exc:  # noqa: BLE001 - demo: log everything
            print(json.dumps({
                "status": "FAILED",
                "messageId": record["messageId"],
                "receiveCount": receive_count,
                "error": str(exc),
            }))
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}


# thumbnail

def make_thumbnail(bucket, key, size, receive_count):
    if not key.lower().endswith(IMAGE_EXTENSIONS):
        # The "poison message": this will never succeed, no matter how many
        # times SQS redelivers it. After 3 receives it lands in the DLQ.
        raise ValueError(f"not an image: {key}")

    # A real worker would resize with Pillow. We copy, which is enough to show
    # the important rule: write OUTSIDE the prefix that triggers you
    # (uploads/ -> thumbs/), or every output re-triggers the pipeline.
    name = key.rsplit("/", 1)[-1]
    dest = f"{THUMBS_PREFIX}{name}"
    s3.copy_object(Bucket=bucket, Key=dest, CopySource={"Bucket": bucket, "Key": key})
    print(json.dumps({
        "worker": "thumbnail", "status": "OK", "source": key,
        "thumbnail": dest, "receiveCount": receive_count,
    }))


def thumbnail_handler(event, context):
    return run_batch(event, make_thumbnail)


# metadata

def record_metadata(bucket, key, size, receive_count):
    head = s3.head_object(Bucket=bucket, Key=key)
    print(json.dumps({
        "worker": "metadata", "status": "OK", "key": key, "bytes": size,
        "contentType": head.get("ContentType"), "etag": head.get("ETag"),
        "receiveCount": receive_count,
    }))


def metadata_handler(event, context):
    return run_batch(event, record_metadata)
