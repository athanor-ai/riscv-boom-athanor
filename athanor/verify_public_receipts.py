#!/usr/bin/env python3
"""Verify public Athanor receipt packages in this fork.

The verifier is intentionally small: each package under ``athanor_artifacts``
must provide ``SHA256SUMS`` and any ``receipt.json`` must parse. Replay scripts
remain package-local because they depend on the caller's pinned Yosys/Liberty
paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = REPO_ROOT / "athanor_artifacts"
# Split literals so this verifier's own source never contains the forbidden
# strings it scans for. This is a manifest-bound structural backstop; the
# comprehensive committed-tree leak authority is ``export_safety_gate.py``
# (ATH-2960).
FORBIDDEN_EXPORT_STRINGS = (
    "/" + "workdir",
    "athanor-" + "kairos-runall",
    "/" + "home/",
    "azure" + "user",
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_sums(package: Path) -> list[str]:
    problems: list[str] = []
    sums_path = package / "SHA256SUMS"
    if not sums_path.is_file():
        return [f"{package.relative_to(REPO_ROOT)} missing SHA256SUMS"]
    for lineno, raw in enumerate(sums_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            expected, rel = raw.split(maxsplit=1)
        except ValueError:
            problems.append(f"{sums_path.relative_to(REPO_ROOT)}:{lineno}: malformed line")
            continue
        rel = rel.removeprefix("./")
        target = package / rel
        if not target.is_file():
            problems.append(f"{sums_path.relative_to(REPO_ROOT)}:{lineno}: missing {rel}")
            continue
        got = _sha256(target)
        if got != expected:
            problems.append(
                f"{target.relative_to(REPO_ROOT)} sha256 mismatch: {got} != {expected}"
            )
    return problems


def _verify_receipt_json(package: Path) -> list[str]:
    receipt = package / "receipt.json"
    if not receipt.exists():
        return []
    try:
        json.loads(receipt.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{receipt.relative_to(REPO_ROOT)} JSON parse failed: {exc}"]
    return []


def _manifest_bound_files(package: Path) -> list[Path]:
    """Files the package actually SHIPS: everything in SHA256SUMS, plus the
    manifest and receipt themselves. This deliberately EXCLUDES generated
    working-tree artifacts (e.g. ``*.replay.log``, which embed the caller's
    pinned tool paths) so a verifier run after ``replay.sh`` does not self-trip
    on its own logs, while still fail-closed on every shipped artifact."""
    files: list[Path] = []
    sums_path = package / "SHA256SUMS"
    if sums_path.is_file():
        for raw in sums_path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            parts = raw.split(maxsplit=1)
            if len(parts) == 2:
                files.append(package / parts[1].removeprefix("./"))
    for extra in (sums_path, package / "receipt.json", package / "README.md"):
        if extra not in files:
            files.append(extra)
    return files


def _verify_public_export_clean(package: Path) -> list[str]:
    problems: list[str] = []
    for path in sorted(set(_manifest_bound_files(package))):
        if not path.is_file():
            continue
        try:
            data = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for forbidden in FORBIDDEN_EXPORT_STRINGS:
            if forbidden in data:
                problems.append(
                    f"{path.relative_to(REPO_ROOT)} contains public-export leak: {forbidden}"
                )
    return problems


def verify(root: Path = ARTIFACT_ROOT) -> list[str]:
    # A capture-track fork (e.g. riscv-boom-athanor) legitimately has no proof
    # packages yet -- "no artifacts yet" is not a failure. Fail-closed means
    # "missing when expected," which is a separate content check; the export-safety
    # leak scan still runs over the whole committed tree regardless.
    if not root.is_dir():
        return []
    problems: list[str] = []
    # A proof package is a dir carrying a SHA256SUMS or a receipt.json. A capture
    # staging dir (e.g. generated_rtl_capture on the capture-track fork) has
    # neither and is not a proof package -> skip it. A dir with a receipt.json but
    # no SHA256SUMS is still a package and IS flagged by _verify_sums.
    packages = [
        p
        for p in sorted(root.iterdir())
        if p.is_dir() and ((p / "SHA256SUMS").is_file() or (p / "receipt.json").is_file())
    ]
    if not packages:
        return []
    for package in packages:
        problems.extend(_verify_sums(package))
        problems.extend(_verify_receipt_json(package))
        problems.extend(_verify_public_export_clean(package))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ARTIFACT_ROOT,
        help="artifact package root, default: athanor_artifacts",
    )
    args = parser.parse_args(argv)

    problems = verify(args.artifact_root)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print(f"OK: verified public receipts under {args.artifact_root.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
