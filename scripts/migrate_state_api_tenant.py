#!/usr/bin/env python3
"""Copy state-api DynamoDB items from pk IMC#innermost → MJC#marrow.

Checkpoints and lease fields use pk = f\"{company_id}#{repository_id}\".
Renaming the CLI tenant without migrating leaves old rows invisible.

Environment:
  AWS_PROFILE / AWS_REGION (default us-east-1)
  STATE_TABLE_NAME — DynamoDB table name (required)

  python3 scripts/migrate_state_api_tenant.py
  python3 scripts/migrate_state_api_tenant.py --apply

Optional overrides:
  --from-company IMC --from-repo innermost --to-company MJC --to-repo marrow
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
from typing import Any

DEFAULT_REGION = "us-east-1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--table", default=os.environ.get("STATE_TABLE_NAME", "").strip())
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", DEFAULT_REGION))
    parser.add_argument("--from-company", default="IMC")
    parser.add_argument("--from-repo", default="innermost")
    parser.add_argument("--to-company", default="MJC")
    parser.add_argument("--to-repo", default="marrow")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.table:
        print("error: set STATE_TABLE_NAME or pass --table", file=sys.stderr)
        return 2

    try:
        import boto3
        from boto3.dynamodb.conditions import Attr
    except ImportError:
        print("error: pip install boto3", file=sys.stderr)
        return 2

    old_pk = f"{args.from_company}#{args.from_repo}"
    new_pk = f"{args.to_company}#{args.to_repo}"
    tc, tr = args.to_company, args.to_repo

    table = boto3.resource("dynamodb", region_name=args.region).Table(args.table)
    items: list[dict[str, Any]] = []
    start_key = None
    while True:
        kw: dict[str, Any] = {"FilterExpression": Attr("pk").eq(old_pk)}
        if start_key:
            kw["ExclusiveStartKey"] = start_key
        resp = table.scan(**kw)
        items.extend(resp.get("Items", []))
        start_key = resp.get("LastEvaluatedKey")
        if not start_key:
            break

    print(f"Found {len(items)} items with pk={old_pk!r} in table {args.table!r}")
    for it in items[:10]:
        print(f"  sk={it.get('sk')!r} company_id={it.get('company_id')!r} repo={it.get('repository_id')!r}")
    if len(items) > 10:
        print(f"  … {len(items) - 10} more")

    if not args.apply:
        print("\nDry run. Re-run with --apply to copy to new pk and delete old items.")
        return 0

    with table.batch_writer() as batch:
        for it in items:
            new_item = copy.deepcopy(it)
            new_item["pk"] = new_pk
            new_item["company_id"] = tc
            new_item["repository_id"] = tr
            batch.put_item(Item=new_item)
        for it in items:
            batch.delete_item(Key={"pk": it["pk"], "sk": it["sk"]})

    print(f"Migrated {len(items)} items to pk={new_pk!r} (old rows removed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
