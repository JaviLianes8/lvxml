"""Copy NI's LVXMLSchema.xsd from a local LabVIEW install into tests/fixtures/ni.

The schema belongs to NI and is not part of the repository. The tests that validate
against it skip until this script has copied it; the copy is checked against the size
and sha256 recorded in tests/fixtures/ni/MANIFEST.json.

    python scripts/capture_ni.py [path-to-LVXMLSchema.xsd]
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "ni"


def main(argv: list[str]) -> int:
    manifest = json.loads((FOLDER / "MANIFEST.json").read_text(encoding="utf-8"))
    failed = 0
    for name, entry in manifest.items():
        source = Path(argv[0]) if argv else Path(entry["origin"])
        if not source.is_file():
            print(f"{name}: not found at {source}")
            failed += 1
            continue
        body = source.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if len(body) != entry["size"] or digest != entry["sha256"]:
            print(f"{name}: got {len(body)} bytes, sha256 {digest}; manifest differs")
            failed += 1
            continue
        (FOLDER / name).write_bytes(body)
        print(f"{name}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
