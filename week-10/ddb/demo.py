"""CS1660 week 10: DynamoDB operations demo.

    uv run demo.py get c-7               # GetItem: one item by full primary key
    uv run demo.py query c-7             # Query: one partition, newest first
    uv run demo.py query c-7 --month 2026-10
    uv run demo.py compare c-7           # Query vs Scan: same answer, different bill
    uv run demo.py product p-03          # Query a GSI

Seed the table first with load.py. Table name comes from TABLE_NAME (default: cs1660-orders-demo).
"""

import argparse
import json
import os
import sys
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key

TABLE_NAME = os.environ.get("TABLE_NAME", "cs1660-orders-demo")
REGION = os.environ.get("AWS_REGION", "us-east-1")

table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)


# helpers

def header(text):
    print(f"\n=== {text} " + "=" * max(0, 60 - len(text)))


def _num(o):
    if isinstance(o, Decimal):
        return int(o) if o % 1 == 0 else float(o)
    return str(o)


def show(item):
    print("  " + json.dumps(item, default=_num))


def capacity(resp):
    """pull the rcu count out of a response."""
    return resp.get("ConsumedCapacity", {}).get("CapacityUnits", 0)


# subcommands

def get(args):
    """getitem — you need the full primary key (pk + sk)."""
    order_id = args.order_id
    if order_id is None:
        first = table.query(KeyConditionExpression=Key("customerId").eq(args.customer), Limit=1)
        if not first["Items"]:
            sys.exit(f"no orders for {args.customer}; run load.py first")
        order_id = first["Items"][0]["orderId"]
    header(f"GetItem customerId={args.customer} orderId={order_id}")
    resp = table.get_item(Key={"customerId": args.customer, "orderId": order_id},
                          ReturnConsumedCapacity="TOTAL")
    show(resp.get("Item", "NOT FOUND"))
    print(f"  consumed {capacity(resp)} RCU")


def query(args):
    """query one partition, optionally filtered to a month."""
    cond = Key("customerId").eq(args.customer)
    label = f"customerId={args.customer}"
    if args.month:
        cond = cond & Key("orderId").begins_with(args.month)
        label += f" AND begins_with(orderId, {args.month!r})"
    header(f"Query {label}, newest first")
    resp = table.query(KeyConditionExpression=cond,
                       ScanIndexForward=False,
                       ConsistentRead=args.consistent,
                       ReturnConsumedCapacity="TOTAL")
    for item in resp["Items"][:10]:
        show(item)
    if resp["Count"] > 10:
        print(f"  ... {resp['Count'] - 10} more")
    print(f"  {resp['Count']} items, consumed {capacity(resp)} RCU"
          f" ({'strongly' if args.consistent else 'eventually'} consistent)")


def compare(args):
    """same question, two ways — shows why scan is expensive."""
    header(f"Query: count orders for {args.customer}")
    t0 = time.perf_counter()
    q = table.query(KeyConditionExpression=Key("customerId").eq(args.customer),
                    Select="COUNT", ReturnConsumedCapacity="TOTAL")
    q_ms = (time.perf_counter() - t0) * 1000
    print(f"  count={q['Count']}  scanned={q['ScannedCount']}  consumed {capacity(q)} RCU  ({q_ms:.0f} ms)")

    header(f"Scan + FilterExpression: count orders for {args.customer}")
    kwargs = {"FilterExpression": Attr("customerId").eq(args.customer),
              "Select": "COUNT", "ReturnConsumedCapacity": "TOTAL"}
    count = scanned = pages = 0
    rcu = 0.0
    t0 = time.perf_counter()
    while True:
        s = table.scan(**kwargs)
        count += s["Count"]
        scanned += s["ScannedCount"]
        rcu += capacity(s)
        pages += 1
        if "LastEvaluatedKey" not in s:
            break
        kwargs["ExclusiveStartKey"] = s["LastEvaluatedKey"]
    s_ms = (time.perf_counter() - t0) * 1000
    print(f"  count={count}  scanned={scanned}  pages={pages}  consumed {rcu} RCU  ({s_ms:.0f} ms)")
    print("\n  same answer. the scan read every item in the table and filtered after.")


def product(args):
    """gsi query vs table scan for the same product — the whole point of indexes."""
    header(f"Query GSI by-product, productId={args.product_id}")
    t0 = time.perf_counter()
    resp = table.query(IndexName="by-product",
                       KeyConditionExpression=Key("productId").eq(args.product_id),
                       ScanIndexForward=False,
                       ReturnConsumedCapacity="INDEXES")
    gsi_ms = (time.perf_counter() - t0) * 1000
    gsi_rcu = capacity(resp)
    for item in resp["Items"][:10]:
        show(item)
    if resp["Count"] > 10:
        print(f"  ... {resp['Count'] - 10} more")
    print(f"  {resp['Count']} items, {gsi_rcu} RCU, {gsi_ms:.0f} ms (always eventually consistent)")

    header(f"Scan + filter for productId={args.product_id}")
    kwargs = {"FilterExpression": Attr("productId").eq(args.product_id),
              "ReturnConsumedCapacity": "TOTAL"}
    items = []
    scan_rcu = 0.0
    t0 = time.perf_counter()
    while True:
        s = table.scan(**kwargs)
        items.extend(s["Items"])
        scan_rcu += capacity(s)
        if "LastEvaluatedKey" not in s:
            break
        kwargs["ExclusiveStartKey"] = s["LastEvaluatedKey"]
    scan_ms = (time.perf_counter() - t0) * 1000
    for item in items[:10]:
        show(item)
    if len(items) > 10:
        print(f"  ... {len(items) - 10} more")
    print(f"  {len(items)} items, {scan_rcu} RCU, {scan_ms:.0f} ms")

    print(f"\n  same data. gsi: {gsi_rcu} RCU / {gsi_ms:.0f} ms — scan: {scan_rcu} RCU / {scan_ms:.0f} ms")


# cli entrypoint

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("get"); s.add_argument("customer"); s.add_argument("order_id", nargs="?"); s.set_defaults(fn=get)
    s = sub.add_parser("query"); s.add_argument("customer"); s.add_argument("--month")
    s.add_argument("--consistent", action="store_true"); s.set_defaults(fn=query)
    s = sub.add_parser("compare"); s.add_argument("customer"); s.set_defaults(fn=compare)
    s = sub.add_parser("product"); s.add_argument("product_id"); s.set_defaults(fn=product)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
