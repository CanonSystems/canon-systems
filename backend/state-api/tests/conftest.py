"""Shared fixtures: mocked DynamoDB + FastAPI TestClient."""

from __future__ import annotations

import boto3
import pytest
from fastapi.testclient import TestClient

from state_api.config import Settings, get_settings
from state_api.events import get_event_emitter
from state_api.leases import get_state_store
from state_api.main import app
from state_api.storage import StateStore

TABLE = "test-canon-state"


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def dynamodb_table() -> str:
    pytest.importorskip(
        "moto",
        reason="install state-api with pip install -e '.[test]' for moto",
    )
    from moto import mock_aws

    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName=TABLE,
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        try:
            client.update_time_to_live(
                TableName=TABLE,
                TimeToLiveSpecification={
                    "Enabled": True,
                    "AttributeName": "lease_expires_at",
                },
            )
        except Exception:
            pass
        yield TABLE


@pytest.fixture
def captured_events() -> list:
    return []


@pytest.fixture
def client(dynamodb_table: str, captured_events: list) -> TestClient:
    settings = Settings(state_table_name=dynamodb_table, aws_region="us-east-1")
    store = StateStore(dynamodb_table, "us-east-1")

    def ov_settings() -> Settings:
        return settings

    def ov_store() -> StateStore:
        return store

    def ov_emitter():
        def _emit(ev) -> None:
            captured_events.append(ev)

        return _emit

    app.dependency_overrides[get_settings] = ov_settings
    app.dependency_overrides[get_state_store] = ov_store
    app.dependency_overrides[get_event_emitter] = ov_emitter
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()
