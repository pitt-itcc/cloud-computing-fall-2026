"""Seed the DynamoDB table with sample orders.

    uv run load.py              # 2,000 orders for 20 customers
    uv run load.py --count 500  # fewer if you're in a hurry
"""

import argparse
import os
import random
from datetime import date, timedelta
from decimal import Decimal

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "cs1660-orders-demo")
REGION = os.environ.get("AWS_REGION", "us-east-1")

table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)

CUSTOMERS = [f"c-{n}" for n in range(1, 21)]
PRODUCTS = [f"p-{n:02d}" for n in range(1, 11)]
STATUSES = ["placed", "shipped", "delivered", "returned"]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--count", type=int, default=2000)
    args = p.parse_args()

    rng = random.Random(1660)  # fixed seed so data is the same every run
    start = date(2026, 1, 1)
    print(f"seeding {args.count} orders into {TABLE_NAME}")
    with table.batch_writer() as batch:
        for n in range(args.count):
            day = start + timedelta(days=rng.randrange(300))
            batch.put_item(Item={
                "customerId": rng.choice(CUSTOMERS),
                "orderId": f"{day.isoformat()}#{n:05d}",
                "productId": rng.choice(PRODUCTS),
                "status": rng.choice(STATUSES),
                "total": Decimal(str(round(rng.uniform(5, 250), 2))),
                "version": 1,
            })
    print(f"  done: {args.count} items, {len(CUSTOMERS)} customers, {len(PRODUCTS)} products")


if __name__ == "__main__":
    main()
