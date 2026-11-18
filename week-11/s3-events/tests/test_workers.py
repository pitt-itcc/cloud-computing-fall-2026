"""Local tests: fake SQS batches, moto-mocked S3. No AWS account needed.

    uv run --with boto3 --with "moto[s3]" --with pytest pytest tests/
"""

import json
import os
import sys

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

BUCKET = "eda-demo-test-uploads"


def sqs_record(msg_id, s3_event, receive_count="1"):
    return {
        "messageId": msg_id,
        "body": json.dumps(s3_event),
        "attributes": {"ApproximateReceiveCount": receive_count},
    }


def s3_event(key, size=10):
    return {"Records": [{
        "eventName": "ObjectCreated:Put",
        "s3": {"bucket": {"name": BUCKET}, "object": {"key": key, "size": size}},
    }]}


@pytest.fixture
def workers():
    with mock_aws():
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket=BUCKET)
        s3.put_object(Bucket=BUCKET, Key="uploads/my cat.jpg", Body=b"img", ContentType="image/jpeg")
        s3.put_object(Bucket=BUCKET, Key="uploads/bad.txt", Body=b"nope", ContentType="text/plain")
        import workers as w
        w.s3 = boto3.client("s3")  # rebind inside the mock
        yield w, s3


def test_thumbnail_decodes_key_and_writes_outside_trigger_prefix(workers):
    w, s3 = workers
    out = w.thumbnail_handler({"Records": [sqs_record("m1", s3_event("uploads/my+cat.jpg"))]}, None)
    assert out == {"batchItemFailures": []}
    s3.head_object(Bucket=BUCKET, Key="thumbs/my cat.jpg")  # raises if missing


def test_poison_message_fails_only_itself(workers):
    w, _ = workers
    batch = {"Records": [
        sqs_record("good", s3_event("uploads/my+cat.jpg")),
        sqs_record("bad", s3_event("uploads/bad.txt"), receive_count="2"),
    ]}
    out = w.thumbnail_handler(batch, None)
    assert out == {"batchItemFailures": [{"itemIdentifier": "bad"}]}


def test_metadata_accepts_any_file(workers):
    w, _ = workers
    out = w.metadata_handler({"Records": [sqs_record("m1", s3_event("uploads/bad.txt"))]}, None)
    assert out == {"batchItemFailures": []}


def test_s3_test_event_is_skipped(workers):
    w, _ = workers
    test_event = {"Service": "Amazon S3", "Event": "s3:TestEvent", "Bucket": BUCKET}
    out = w.thumbnail_handler({"Records": [sqs_record("t", test_event)]}, None)
    assert out == {"batchItemFailures": []}
