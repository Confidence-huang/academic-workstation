"""Test that every public schema remains valid JSON and exposes the v0.2.0 matrix contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


class SchemaContractTest(unittest.TestCase):
    """A schema syntax error must fail before any acceptance run is attempted."""

    def test_public_schemas_are_json_documents(self) -> None:
        schema_root = Path(__file__).resolve().parents[1] / "schemas"
        schema_paths = sorted(schema_root.glob("*.json"))
        self.assertGreaterEqual(len(schema_paths), 6)
        for schema_path in schema_paths:
            document = json.loads(schema_path.read_text(encoding="utf-8"))
            self.assertEqual(document["type"], "object", schema_path.name)

    def test_matrix_schema_names_all_gates(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "acceptance-matrix.schema.json"
        document = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertIn("rows", document["required"])
        self.assertIn("gates", document["$defs"]["row"]["required"])


if __name__ == "__main__":
    unittest.main()
