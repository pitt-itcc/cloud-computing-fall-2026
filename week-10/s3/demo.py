"""CS1660 week 10: S3 operations demo.

    uv run demo.py put hello.txt "hello from cs1660"
    uv run demo.py put data/grades.json '{"midterm": 92}'
    uv run demo.py get hello.txt
    uv run demo.py list
    uv run demo.py delete hello.txt

Create the bucket with Terraform first (see terraform/).
Bucket name comes from BUCKET_NAME (default: cs1660-s3-demo-<account-id>).
"""

import argparse
import os
import sys

import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-east-1")
s3 = boto3.client("s3", region_name=REGION)
sts = boto3.client("sts", region_name=REGION)


def bucket_name():
    name = os.environ.get("BUCKET_NAME")
    if name:
        return name
    account = sts.get_caller_identity()["Account"]
    return f"cs1660-s3-demo-{account}"


def header(text):
    print(f"\n=== {text} " + "=" * max(0, 60 - len(text)))


def put(args):
    """upload an object."""
    name = bucket_name()
    header(f"PutObject s3://{name}/{args.key}")
    s3.put_object(Bucket=name, Key=args.key, Body=args.body.encode())
    print(f"  wrote {len(args.body)} bytes to {args.key}")


def get(args):
    """download and print an object."""
    name = bucket_name()
    header(f"GetObject s3://{name}/{args.key}")
    try:
        resp = s3.get_object(Bucket=name, Key=args.key)
        body = resp["Body"].read().decode()
        print(f"  content-type: {resp['ContentType']}")
        print(f"  body: {body}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            sys.exit(f"  not found: {args.key}")
        raise


def list_objects(args):
    """list objects in the bucket."""
    name = bucket_name()
    header(f"ListObjectsV2 s3://{name}/")
    resp = s3.list_objects_v2(Bucket=name, Prefix=args.prefix)
    contents = resp.get("Contents", [])
    if not contents:
        print("  (empty)")
        return
    for obj in contents:
        print(f"  {obj['Key']:40s}  {obj['Size']:>8d} bytes  {obj['LastModified']}")
    print(f"  {len(contents)} objects")


def delete(args):
    """delete one object."""
    name = bucket_name()
    header(f"DeleteObject s3://{name}/{args.key}")
    s3.delete_object(Bucket=name, Key=args.key)
    print(f"  deleted: {args.key}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("put"); s.add_argument("key"); s.add_argument("body"); s.set_defaults(fn=put)
    s = sub.add_parser("get"); s.add_argument("key"); s.set_defaults(fn=get)
    s = sub.add_parser("list"); s.add_argument("--prefix", default=""); s.set_defaults(fn=list_objects)
    s = sub.add_parser("delete"); s.add_argument("key"); s.set_defaults(fn=delete)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
