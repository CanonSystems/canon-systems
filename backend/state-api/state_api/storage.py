"""DynamoDB access for canon-state (single boto3 import site)."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError


def _dynamo_to_plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, dict):
        return {k: _dynamo_to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_dynamo_to_plain(v) for v in value]
    return value


def ledger_record_from_item(item: dict[str, Any]) -> dict[str, Any]:
    """Strip DynamoDB keys and normalize numeric types for JSON/compare."""
    raw = {k: v for k, v in item.items() if k not in ("pk", "sk")}
    return _dynamo_to_plain(raw)  # type: ignore[return-value]


def run_ledger_items_equivalent(stored: dict[str, Any], desired: dict[str, Any]) -> bool:
    """True if ledger payloads match (ignoring pk/sk), after canonical validation."""
    from canon_backend_shared.run_ledger import RunLedgerValidationError, validate_run_ledger_record

    a_raw = ledger_record_from_item(stored)
    b_raw = {k: v for k, v in desired.items() if k not in ("pk", "sk")}
    try:
        a = validate_run_ledger_record(a_raw)
        b = validate_run_ledger_record(b_raw)
    except RunLedgerValidationError:
        return False
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


class RunLedgerStore:
    """DynamoDB table for immutable run-ledger rows (distinct from checkpoint lease state)."""

    def __init__(self, table_name: str, region: str) -> None:
        self._table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    @property
    def table_name(self) -> str:
        return self._table.name

    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None:
        resp = self._table.get_item(Key={"pk": pk, "sk": sk})
        return resp.get("Item")

    def put_if_absent(self, item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """
        Insert a ledger row. Returns ``("created", item)`` or raises ClientError.
        On duplicate key, use :meth:`get_item` + :func:`run_ledger_items_equivalent` outside.
        """
        self._table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
        )
        return ("created", item)

    def query_sk_prefix(self, pk: str, sk_prefix: str, *, limit: int) -> list[dict[str, Any]]:
        resp = self._table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :pre)",
            ExpressionAttributeValues={":pk": pk, ":pre": sk_prefix},
            Limit=limit,
        )
        return list(resp.get("Items", []))


class StateStore:
    """Thin wrapper around DynamoDB Table operations for checkpoints and leases."""

    def __init__(self, table_name: str, region: str) -> None:
        self._table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    @property
    def table_name(self) -> str:
        return self._table.name

    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None:
        resp = self._table.get_item(Key={"pk": pk, "sk": sk})
        return resp.get("Item")

    def put_checkpoint(
        self,
        pk: str,
        sk: str,
        *,
        expected_state_version: int,
        lease_token: str,
        now_epoch: int,
        phase: str,
        phase_status: str,
        updated_at: str,
        new_last_event_id: str,
        handoff_id: str,
        optional_sets: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Conditional update: bump state_version, refresh checkpoint fields, set last_event_id.
        Raises ClientError with code ConditionalCheckFailedException on conflict.
        """
        expr_names: dict[str, str] = {
            "#sv": "state_version",
            "#ph": "phase",
            "#ps": "phase_status",
            "#ua": "updated_at",
            "#leid": "last_event_id",
            "#hid": "handoff_id",
            "#lt": "lease_token",
            "#le": "lease_expires_at",
        }
        expr_vals: dict[str, Any] = {
            ":one": 1,
            ":esv": expected_state_version,
            ":ltok": lease_token,
            ":now": now_epoch,
            ":phase": phase,
            ":pstat": phase_status,
            ":uat": updated_at,
            ":neid": new_last_event_id,
            ":hid": handoff_id,
        }

        update_parts = [
            "#sv = #sv + :one",
            "#ph = :phase",
            "#ps = :pstat",
            "#ua = :uat",
            "#leid = :neid",
            "#hid = :hid",
        ]

        if optional_sets:
            for key, val in optional_sets.items():
                if val is None:
                    continue
                placeholder = f"#k_{key}"
                vph = f":v_{key}"
                expr_names[placeholder] = key
                expr_vals[vph] = val
                update_parts.append(f"{placeholder} = {vph}")

        update_expression = "SET " + ", ".join(update_parts)
        condition = "#sv = :esv AND #lt = :ltok AND #le > :now"

        resp = self._table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression=update_expression,
            ConditionExpression=condition,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_vals,
            ReturnValues="ALL_NEW",
        )
        return resp["Attributes"]

    def acquire_lease(
        self,
        pk: str,
        sk: str,
        *,
        token: str,
        owner_agent_run_id: str,
        owner_actor_id: str,
        acquired_at: int,
        expires_at: int,
        now_epoch: int,
        base_item: dict[str, Any],
        extend_same_owner: bool,
    ) -> None:
        """Claim a new lease or extend an existing same-owner lease (idempotent)."""
        if extend_same_owner:
            self._acquire_lease_extend_same_owner(
                pk,
                sk,
                token=token,
                owner_agent_run_id=owner_agent_run_id,
                expires_at=expires_at,
                now_epoch=now_epoch,
            )
        else:
            self._acquire_lease_fresh(
                pk,
                sk,
                token=token,
                owner_agent_run_id=owner_agent_run_id,
                owner_actor_id=owner_actor_id,
                acquired_at=acquired_at,
                expires_at=expires_at,
                now_epoch=now_epoch,
                base_item=base_item,
            )

    def _acquire_lease_fresh(
        self,
        pk: str,
        sk: str,
        *,
        token: str,
        owner_agent_run_id: str,
        owner_actor_id: str,
        acquired_at: int,
        expires_at: int,
        now_epoch: int,
        base_item: dict[str, Any],
    ) -> None:
        """
        Claim lease when item is missing or prior lease is not live.
        Creates minimal checkpoint shell on first write (state_version=0 if new).
        """
        names: dict[str, str] = {
            "#pk": "pk",
            "#lt": "lease_token",
            "#lo": "lease_owner_agent_run_id",
            "#la": "lease_owner_actor_id",
            "#lac": "lease_acquired_at",
            "#le": "lease_expires_at",
            "#leexp": "lease_expires_at",
            "#sv": "state_version",
            "#schema": "schema_version",
            "#cid": "company_id",
            "#rid": "repository_id",
            "#pid": "plan_id",
            "#tid": "task_id",
            "#wid": "workstream_id",
        }
        vals: dict[str, Any] = {
            ":tok": token,
            ":lo": owner_agent_run_id,
            ":la": owner_actor_id,
            ":lac": acquired_at,
            ":le": expires_at,
            ":now": now_epoch,
            ":zero": 0,
            ":one": 1,
            ":cid": base_item["company_id"],
            ":rid": base_item["repository_id"],
            ":pid": base_item["plan_id"],
            ":tid": base_item["task_id"],
            ":wid": base_item["workstream_id"],
        }
        # Condition: new item OR lease not live
        cond = (
            "attribute_not_exists(#pk) OR attribute_not_exists(#leexp) OR #leexp <= :now"
        )
        update = (
            "SET #schema = if_not_exists(#schema, :one), "
            "#cid = if_not_exists(#cid, :cid), #rid = if_not_exists(#rid, :rid), "
            "#pid = if_not_exists(#pid, :pid), #tid = if_not_exists(#tid, :tid), "
            "#wid = if_not_exists(#wid, :wid), "
            "#sv = if_not_exists(#sv, :zero), "
            "#lt = :tok, #lo = :lo, #la = :la, #lac = :lac, #le = :le"
        )
        self._table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression=update,
            ConditionExpression=cond,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=vals,
        )

    def _acquire_lease_extend_same_owner(
        self,
        pk: str,
        sk: str,
        *,
        token: str,
        owner_agent_run_id: str,
        expires_at: int,
        now_epoch: int,
    ) -> None:
        """Idempotent same-owner acquire: bump expiry only; token unchanged."""
        names = {
            "#lt": "lease_token",
            "#lo": "lease_owner_agent_run_id",
            "#le": "lease_expires_at",
        }
        vals: dict[str, Any] = {
            ":tok": token,
            ":lo": owner_agent_run_id,
            ":le": expires_at,
            ":now": now_epoch,
        }
        cond = "#lt = :tok AND #lo = :lo AND #le > :now"
        update = "SET #le = :le"
        self._table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression=update,
            ConditionExpression=cond,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=vals,
        )

    def renew_lease(
        self,
        pk: str,
        sk: str,
        *,
        lease_token: str,
        expires_at: int,
        now_epoch: int,
    ) -> None:
        names = {"#lt": "lease_token", "#le": "lease_expires_at"}
        vals: dict[str, Any] = {
            ":tok": lease_token,
            ":le": expires_at,
            ":now": now_epoch,
        }
        cond = "#lt = :tok AND #le > :now"
        update = "SET #le = :le"
        self._table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression=update,
            ConditionExpression=cond,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=vals,
        )

    def release_lease(
        self,
        pk: str,
        sk: str,
        *,
        lease_token: str,
    ) -> bool:
        """
        Clear lease attributes if token matches.
        Returns True if update applied; False if condition failed (caller may probe).
        """
        names = {
            "#lt": "lease_token",
            "#lo": "lease_owner_agent_run_id",
            "#la": "lease_owner_actor_id",
            "#lac": "lease_acquired_at",
            "#le": "lease_expires_at",
        }
        vals: dict[str, Any] = {":tok": lease_token}
        update = "REMOVE #lt, #lo, #la, #lac, #le"
        cond = "#lt = :tok"
        try:
            self._table.update_item(
                Key={"pk": pk, "sk": sk},
                UpdateExpression=update,
                ConditionExpression=cond,
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=vals,
            )
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise
