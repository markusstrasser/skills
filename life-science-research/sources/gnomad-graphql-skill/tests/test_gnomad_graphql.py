from __future__ import annotations

import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


SCRIPT = Path(__file__).parents[1] / "scripts" / "gnomad_graphql.py"
SPEC = importlib.util.spec_from_file_location("gnomad_graphql", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
gnomad_graphql = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gnomad_graphql)


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class ExecuteTests(unittest.TestCase):
    @patch.object(gnomad_graphql, "urlopen")
    def test_uses_stdlib_http_without_optional_dependencies(self, mock_open: object) -> None:
        mock_open.return_value = FakeResponse({"data": {"meta": {"ok": True}}})

        result = gnomad_graphql.execute({"query": "query { meta { ok } }"})

        self.assertTrue(result["ok"])
        request = mock_open.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.headers["Content-type"], "application/json")

    @patch.object(gnomad_graphql, "urlopen")
    def test_http_error_includes_response_body(self, mock_open: object) -> None:
        mock_open.side_effect = HTTPError(
            gnomad_graphql.ENDPOINT,
            400,
            "Bad Request",
            {},
            io.BytesIO(b'{"error":"unknown dataset"}'),
        )

        result = gnomad_graphql.execute({"query": "query { broken }"})

        self.assertFalse(result["ok"])
        self.assertIn("unknown dataset", result["error"]["message"])


if __name__ == "__main__":
    unittest.main()
