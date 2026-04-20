import json

from memory_layer.aws_secrets import parse_secret_string


def test_parse_secret_string_json() -> None:
    raw = json.dumps(
        {
            "CANON_HTTP_BEARER_TOKEN": "tok",
            "KNOWLEDGE_API_URL": "http://example",
            "FLAG": True,
        }
    )
    assert parse_secret_string(raw) == {
        "CANON_HTTP_BEARER_TOKEN": "tok",
        "KNOWLEDGE_API_URL": "http://example",
        "FLAG": "True",
    }


def test_parse_secret_string_dotenv() -> None:
    body = "# c\nCANON_HTTP_BEARER_TOKEN=abc\nFOO=bar\n"
    assert parse_secret_string(body) == {"CANON_HTTP_BEARER_TOKEN": "abc", "FOO": "bar"}
