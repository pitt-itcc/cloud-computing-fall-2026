#!/usr/bin/env python3
"""
image pipeline worker — polls an sqs queue and processes s3 images.

usage:
    python worker.py --queue-url <url> --task resize
    python worker.py --queue-url <url> --task metadata
    python worker.py --queue-url <url> --task archive
"""

import argparse
import json
import tempfile
from pathlib import Path

import boto3
from PIL import Image

REGION = "us-east-1"
THUMBNAIL_SIZE = (200, 200)

sqs = boto3.client("sqs", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)


def parse_s3_event(message_body: str) -> tuple[str, str]:
    """dig through the sns envelope to get the bucket and key from the
    eventbridge event: SQS body -> SNS Message -> EventBridge detail."""
    sns_envelope = json.loads(message_body)
    event = json.loads(sns_envelope["Message"])
    bucket = event["detail"]["bucket"]["name"]
    key = event["detail"]["object"]["key"]
    return bucket, key


# --- task handlers ---


def resize(bucket: str, key: str):
    with tempfile.NamedTemporaryFile(suffix=Path(key).suffix) as tmp:
        s3.download_file(bucket, key, tmp.name)
        img = Image.open(tmp.name)
        original_size = img.size
        img.thumbnail(THUMBNAIL_SIZE)

        out_key = f"resized/{Path(key).name}"
        out_path = tmp.name + "_thumb" + Path(key).suffix
        img.save(out_path)
        s3.upload_file(out_path, bucket, out_key)

    print(f"  {original_size[0]}x{original_size[1]} -> {img.size[0]}x{img.size[1]}")
    print(f"  saved to s3://{bucket}/{out_key}")


def metadata(bucket: str, key: str):
    with tempfile.NamedTemporaryFile(suffix=Path(key).suffix) as tmp:
        s3.download_file(bucket, key, tmp.name)
        img = Image.open(tmp.name)
        head = s3.head_object(Bucket=bucket, Key=key)

    print(f"  format:       {img.format}")
    print(f"  dimensions:   {img.size[0]}x{img.size[1]}")
    print(f"  mode:         {img.mode}")
    print(f"  content-type: {head['ContentType']}")
    print(f"  size:         {head['ContentLength']} bytes")


def archive(bucket: str, key: str):
    dest_key = f"archive/{Path(key).name}"
    s3.copy_object(
        Bucket=bucket,
        CopySource={"Bucket": bucket, "Key": key},
        Key=dest_key,
        StorageClass="GLACIER_IR",
    )
    print(f"  copied to s3://{bucket}/{dest_key} (GLACIER_IR)")


TASKS = {
    "resize": resize,
    "metadata": metadata,
    "archive": archive,
}


def poll(queue_url: str, task: str):
    handler = TASKS[task]
    print(f"[{task}] polling {queue_url}")
    print(f"[{task}] waiting for messages... (ctrl-c to stop)\n")

    while True:
        resp = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )

        for msg in resp.get("Messages", []):
            bucket, key = parse_s3_event(msg["Body"])
            print(f"[{task}] processing s3://{bucket}/{key}")
            handler(bucket, key)
            sqs.delete_message(
                QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"]
            )
            print(f"[{task}] done\n")


def main():
    parser = argparse.ArgumentParser(description="image pipeline sqs worker")
    parser.add_argument("--queue-url", required=True, help="sqs queue url")
    parser.add_argument(
        "--task",
        required=True,
        choices=TASKS.keys(),
        help="worker task type",
    )
    args = parser.parse_args()

    try:
        poll(args.queue_url, args.task)
    except KeyboardInterrupt:
        print(f"\n[{args.task}] shutting down")


if __name__ == "__main__":
    main()
