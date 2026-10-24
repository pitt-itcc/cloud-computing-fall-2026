"""CS1660 week 10: DynamoDB operations demo.

Run each step live, in this order:

    uv run demo.py seed                 # load ~2,000 orders for 20 customers
    uv run demo.py get c-7              # GetItem: one item by full primary key
    uv run demo.py query c-7            # Query: one partition, newest first
    uv run demo.py query c-7 --month 2026-10
    uv run demo.py compare c-7          # Query vs Scan: same answer, different bill
    uv run demo.py page c-7 --limit 5   # pagination with LastEvaluatedKey
    uv run demo.py create               # conditional write vs silent overwrite
    uv run demo.py lock                 # optimistic locking with a version number
    uv run demo.py product p-03         # Query a GSI
    uv run demo.py floats               # the two Decimal bugs from the Lambda slide

The table name comes from TABLE_NAME (default: cs1660-orders-demo).
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import date, timedelta
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

TABLE_NAME = os.environ.get("TABLE_NAME", "cs1660-orders-demo")
REGION = os.environ.get("AWS_REGION", "us-east-1")

table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)

CUSTOMERS = [f"c-{n}" for n in range(1, 21)]
PRODUCTS = [f"p-{n:02d}" for n in range(1, 11)]
STATUSES = ["placed", "shipped", "delivered", "returned"]


# ---------------------------------------------------------------- helpers

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


# ---------------------------------------------------------------- commands

def seed(args):
    """bulk-load orders. batch_writer handles the 25-item chunking for us."""
    rng = random.Random(1660)  # fixed seed so data is the same every run
    start = date(2026, 1, 1)
    header(f"Seeding {args.count} orders into {TABLE_NAME}")
    with table.batch_writer() as batch:
        for n in range(args.count):
            day = start + timedelta(days=rng.randrange(300))
            batch.put_item(Item={
                "customerId": rng.choice(CUSTOMERS),
                "orderId": f"{day.isoformat()}#{n:05d}",   # @note: iso date prefix = free chronological sort
                "productId": rng.choice(PRODUCTS),
                "status": rng.choice(STATUSES),
                "total": Decimal(str(round(rng.uniform(5, 250), 2))),  # @note: must be Decimal, not float
                "version": 1,
            })
    print(f"  done: {args.count} items, {len(CUSTOMERS)} customers, {len(PRODUCTS)} products")


def get(args):
    """getitem — you need the full primary key (pk + sk)."""
    order_id = args.order_id
    if order_id is None:  # no order specified, just grab the first one
        first = table.query(KeyConditionExpression=Key("customerId").eq(args.customer), Limit=1)
        if not first["Items"]:
            sys.exit(f"no orders for {args.customer}; run seed first")
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
                       ScanIndexForward=False,           # newest first
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
    while True:  # scan paginates at 1 MB
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


def page(args):
    """paginate through a partition like an api route with ?limit= would."""
    header(f"Paginate {args.customer}, Limit={args.limit}")
    kwargs = {"KeyConditionExpression": Key("customerId").eq(args.customer),
              "Limit": args.limit, "ScanIndexForward": False}
    n = 0
    while True:
        n += 1
        resp = table.query(**kwargs)
        ids = [i["orderId"] for i in resp["Items"]]
        lek = resp.get("LastEvaluatedKey")
        print(f"  page {n}: {ids}")
        print(f"          LastEvaluatedKey = {lek}")
        if not lek:
            print("  no LastEvaluatedKey: that was the last page")
            break
        kwargs["ExclusiveStartKey"] = lek  # pick up where we left off
        if n >= args.max_pages:
            print(f"  (stopping after {args.max_pages} pages; the client would keep going)")
            break


def create(args):
    """putitem with and without attribute_not_exists — create-only vs overwrite."""
    key = {"customerId": "c-7", "orderId": "2026-10-28#99999"}
    table.delete_item(Key=key)  # clean slate so we can re-run

    header("1. PutItem with attribute_not_exists: new order")
    table.put_item(Item={**key, "productId": "p-01", "total": Decimal("42.50"),
                         "giftNote": "Happy birthday", "version": 1},
                   ConditionExpression="attribute_not_exists(orderId)")
    show(table.get_item(Key=key)["Item"])

    header("2. Same key again, same condition")
    try:
        table.put_item(Item={**key, "productId": "p-02", "total": Decimal("1.00"), "version": 1},
                       ConditionExpression="attribute_not_exists(orderId)")
    except ClientError as e:
        print(f"  {e.response['Error']['Code']}: the database refused the write")
        print("  in an API handler this becomes a 409 Conflict, not a 500")

    header("3. Same key again, NO condition")
    table.put_item(Item={**key, "productId": "p-02", "total": Decimal("1.00"), "version": 1})
    show(table.get_item(Key=key)["Item"])
    print("  succeeded silently: the giftNote is gone, the order was replaced")


def lock(args):
    """optimistic locking — reject the write if someone else changed it first."""
    key = {"customerId": "c-7", "orderId": "2026-10-28#99998"}
    table.put_item(Item={**key, "productId": "p-01", "total": Decimal("20.00"), "version": 1})

    def update(who, new_total, expected):
        print(f"  {who}: SET total={new_total} IF version = {expected}")
        table.update_item(
            Key=key,
            UpdateExpression="SET #t = :t, version = :next",
            ConditionExpression="version = :cur",
            ExpressionAttributeNames={"#t": "total"},
            ExpressionAttributeValues={":t": Decimal(new_total), ":cur": expected,
                                       ":next": expected + 1},
        )

    header("Two clients read the same order")
    a = table.get_item(Key=key)["Item"]
    b = table.get_item(Key=key)["Item"]
    print(f"  client A read version {a['version']}, client B read version {b['version']}")

    header("Client A writes first")
    update("A", "25.00", a["version"])
    print("  ok, version is now 2")

    header("Client B writes with its stale version")
    try:
        update("B", "30.00", b["version"])
    except ClientError as e:
        print(f"  {e.response['Error']['Code']}: B's write was rejected")
        print("  instead of silently erasing A's change. API response: 412 Precondition Failed")
    show(table.get_item(Key=key)["Item"])


def product(args):
    """gsi query vs table scan for the same product — the whole point of indexes."""

    # @note: gsi query — goes straight to the right partition
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

    # @note: same question without the gsi — full table scan + filter
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


def floats(args):
    """the two decimal gotchas you'll hit in every lambda handler."""
    key = {"customerId": "c-7", "orderId": "2026-10-28#99997"}

    header("Bug 1: writing a Python float")
    body = '{"total": 42.5}'
    try:
        table.put_item(Item={**key, **json.loads(body)})
    except TypeError as e:
        print(f"  TypeError: {e}")
    print("  fix: json.loads(body, parse_float=Decimal)")
    table.put_item(Item={**key, **json.loads(body, parse_float=Decimal)})
    print("  ok")

    header("Bug 2: returning what you read")
    item = table.get_item(Key=key)["Item"]
    print(f"  boto3 gives back: {item!r}")
    try:
        json.dumps(item)
    except TypeError as e:
        print(f"  json.dumps -> TypeError: {e}")
    print(f"  fix: json.dumps(item, default=str) -> {json.dumps(item, default=str)}")
    table.delete_item(Key=key)


# ---------------------------------------------------------------- cli

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("seed"); s.add_argument("--count", type=int, default=2000); s.set_defaults(fn=seed)
    s = sub.add_parser("get"); s.add_argument("customer"); s.add_argument("order_id", nargs="?"); s.set_defaults(fn=get)
    s = sub.add_parser("query"); s.add_argument("customer"); s.add_argument("--month")
    s.add_argument("--consistent", action="store_true"); s.set_defaults(fn=query)
    s = sub.add_parser("compare"); s.add_argument("customer"); s.set_defaults(fn=compare)
    s = sub.add_parser("page"); s.add_argument("customer"); s.add_argument("--limit", type=int, default=5)
    s.add_argument("--max-pages", type=int, default=4); s.set_defaults(fn=page)
    sub.add_parser("create").set_defaults(fn=create)
    sub.add_parser("lock").set_defaults(fn=lock)
    s = sub.add_parser("product"); s.add_argument("product_id"); s.set_defaults(fn=product)
    sub.add_parser("floats").set_defaults(fn=floats)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
