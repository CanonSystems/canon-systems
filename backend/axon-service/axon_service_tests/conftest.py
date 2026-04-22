from __future__ import annotations
import os
import pytest

pytest.importorskip("moto")
pytest.importorskip("httpx")

import boto3
from moto import mock_aws
from fastapi.testclient import TestClient

os.environ.setdefault("AXON_AWS_REGION", "us-east-1")
os.environ.setdefault("AXON_S3_BUCKET", "axon-test-bucket")
os.environ.setdefault("AXON_META_TABLE_NAME", "axon-test-meta")
os.environ.setdefault("AXON_SERVICE_TOKEN", "test-token")


@pytest.fixture
def aws():
    with mock_aws():
        yield


@pytest.fixture
def s3_bucket(aws):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="axon-test-bucket")
    return "axon-test-bucket"


@pytest.fixture
def meta_table(aws):
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="axon-test-meta",
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
    ddb.meta.client.get_waiter("table_exists").wait(TableName="axon-test-meta")
    return "axon-test-meta"


@pytest.fixture
def captured_events():
    events = []

    def emitter(e):
        events.append(e)

    return events, emitter


@pytest.fixture
def client(s3_bucket, meta_table, captured_events):
    from axon_service.config import get_settings
    from axon_service.events import get_event_emitter
    from axon_service.main import create_app

    get_settings.cache_clear()
    app = create_app()

    _events, emitter = captured_events

    def _override_emitter():
        return emitter

    app.dependency_overrides[get_event_emitter] = _override_emitter
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    get_settings.cache_clear()
