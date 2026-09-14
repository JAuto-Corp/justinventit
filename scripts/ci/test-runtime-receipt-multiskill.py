#!/usr/bin/env python3
"""Receipt schema/validator tests for the optional `additional_skills` section (multi-skill availability)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ci"))
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("vrr", ROOT / "scripts/ci/validate-runtime-receipt.py")
vrr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vrr)
SCHEMA = json.loads((ROOT / "scripts/ci/fixtures/runtime-skill-receipt.schema.json").read_text(encoding="utf-8"))
FIXTURE = ROOT / "scripts/ci/fixtures/runtime-availability-valid"


def artifact(root: Path, rel: str, payload: bytes) -> dict:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"path": rel, "class": "regular", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


class Fixture(unittest.TestCase):
    def test_frozen_one_skill_fixture_still_validates(self) -> None:
        receipt = json.loads((FIXTURE / "receipt.json").read_text(encoding="utf-8"))
        vrr.validate_receipt(SCHEMA, receipt, FIXTURE)


class AdditionalSkills(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="jv-receipt."))
        shutil.copytree(FIXTURE / "artifacts", self.tmp / "artifacts")
        shutil.copy(FIXTURE / "receipt.json", self.tmp / "receipt.json")
        self.receipt = json.loads((FIXTURE / "receipt.json").read_text(encoding="utf-8"))
        body = b"---\nname: ponytail\n---\n"
        self.receipt["additional_skills"] = {"ponytail": {
            "codex": {"status": 0, "target_count": 1, "no_project_target_count": 0,
                      "observed_absolute_path": "/tmp/x/project/.agents/skills/ponytail/SKILL.md",
                      "derived_repository_path": ".agents/skills/ponytail/SKILL.md",
                      "skill_bytes": len(body), "skill_sha256": hashlib.sha256(body).hexdigest(),
                      "artifacts": {"project": artifact(self.tmp, "artifacts/codex-project-ponytail.json", b"{}\n"),
                                    "project_stderr": artifact(self.tmp, "artifacts/codex-project-ponytail.stderr", b"")}},
            "claude_target_count": 1}}

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_valid_additional_skill_passes(self) -> None:
        vrr.validate_receipt(SCHEMA, self.receipt, self.tmp)

    def test_tampered_artifact_digest_fails(self) -> None:
        (self.tmp / "artifacts/codex-project-ponytail.json").write_bytes(b"{\"tampered\": true}\n")
        with self.assertRaises(vrr.ReceiptValidationError):
            vrr.validate_receipt(SCHEMA, self.receipt, self.tmp)

    def test_unreferenced_artifact_breaks_closure(self) -> None:
        (self.tmp / "artifacts/codex-project-caveman.json").write_bytes(b"{}\n")
        with self.assertRaises(vrr.ReceiptValidationError):
            vrr.validate_receipt(SCHEMA, self.receipt, self.tmp)

    def test_wrong_counts_or_names_fail_schema(self) -> None:
        bad = json.loads(json.dumps(self.receipt)); bad["additional_skills"]["ponytail"]["codex"]["target_count"] = 2
        with self.assertRaises(vrr.ReceiptValidationError):
            vrr.validate_receipt(SCHEMA, bad, self.tmp)
        bad = json.loads(json.dumps(self.receipt)); bad["additional_skills"]["ponytail"]["claude_target_count"] = 0
        with self.assertRaises(vrr.ReceiptValidationError):
            vrr.validate_receipt(SCHEMA, bad, self.tmp)
        bad = json.loads(json.dumps(self.receipt)); bad["additional_skills"]["frontend-design"] = bad["additional_skills"].pop("ponytail")
        with self.assertRaises(vrr.ReceiptValidationError):
            vrr.validate_receipt(SCHEMA, bad, self.tmp)
        bad = json.loads(json.dumps(self.receipt)); bad["additional_skills"]["ponytail"]["extra_field"] = 1
        with self.assertRaises(vrr.ReceiptValidationError):
            vrr.validate_receipt(SCHEMA, bad, self.tmp)


if __name__ == "__main__":
    unittest.main(verbosity=1)
