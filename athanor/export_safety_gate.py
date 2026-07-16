#!/usr/bin/env python3
"""ATH-2960 fork export-safety gate for the public Athanor RTL forks.

This is a fail-closed CI gate for the public ``openc910-athanor`` /
``riscv-boom-athanor`` forks. It scans the **committed bytes** of every tracked
file at a ref (default ``HEAD``) via ``git ls-tree`` + ``git show <ref>:<path>``,
never the working tree, so locally generated artifacts -- in particular
``*.replay.log`` files, which embed the caller's pinned tool paths -- can neither
false-trip the gate nor let a real committed leak hide behind "it is only a
local file".

It scans BYTES, not ``git grep``, on purpose: the packages mark ``*.log`` /
``*.sv`` / ``*.v`` as ``binary`` in ``.gitattributes``, and ``git grep -I``
silently SKIPS binary files -- so a token or key inside a ``*.pinned.log`` (the
verbatim tool output where a real credential is likeliest to leak) would slip
past a git-grep scan. Reading committed bytes and matching directly closes that
gap regardless of ``.gitattributes``. (ATH-2960, blind spot caught by Perry on
PR #4.)

Two tiers (customer-surface owner ruling, ATH-2960):

  BLOCK  hard-safety leaks; any committed-tree hit fails the gate:
           - internal absolute filesystem paths and home directories
           - tmp / tool-cache paths
           - the cloud build username
           - the internal ops-repo name
           - confidential customer names
           - secret tokens (GitHub, Slack, AWS, OpenAI/Anthropic, private keys)

  WARN   conscious-choice internal metadata; surfaced, never blocks:
           - internal Linear ticket IDs
           - the private Kairos-repo pointer
         These are not secrets or paths -- their exposure is a deliberate
         per-artifact choice and some is intentional/team-settled, so the gate
         reports them for a conscious keep/scrub decision rather than blocking.

It also runs the package receipt verifier (SHA256 manifest + ``receipt.json``
parse) and is fail-closed if that verifier is missing or errors.

The forbidden strings below are assembled from fragments so this gate's OWN
source never contains a verbatim forbidden literal -- otherwise it would
self-trip on every run. (The receipt verifier uses the same convention.)

Exit codes:
  0  clean (WARN findings allowed)
  1  a BLOCK leak was found, or the receipt verifier failed
  2  the gate itself could not run (not in a git repo, git missing, ...)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


# --- BLOCK tiers. Regexes are fragment-built so this file holds no verbatim leak.
#
# These forks are forks-OF-UPSTREAM (OpenC910, riscv-boom/FireSim). Upstream
# ships its OWN host paths in its OWN files (its CI references upstream home dirs
# and a FireSim temp instance-data file) -- that is public-upstream content, NOT
# our leak, and must not be flagged (scrubbing it would diverge the fork). So
# two tiers (patterns fragment-built so this file holds no verbatim leak string):
#
#   BLOCK_ALWAYS  our unambiguous internal markers + secrets. Never legitimate
#                 anywhere, in upstream or our files -> block across the whole tree.
#   BLOCK_SCOPED  ambiguous host paths. Our leak risk is a VM path landing in an
#                 artifact WE add; upstream's own host paths are fine. So block
#                 these ONLY under OUR_ADDED_PREFIXES.
BLOCK_ALWAYS: list[tuple[str, str]] = [
    ("internal workdir path", "/work" + "dir"),
    ("cloud build username", "azure" + "user"),
    ("internal ops repo", "athanor-" + "kairos-runall"),
    # Export-safety hardening (Quan): the internal project namespace used as a
    # schema or module PATH -- e.g. a receipt "schema": "<ns>.<ticket>..." or a
    # "from <ns>.sub import ..." line. A public fork has no legitimate reason to
    # carry an internal module/schema path (owner ruling: BLOCK, fail-closed; any
    # future legit case goes through the audited allowlist, not a weakened
    # pattern). The repo POINTER "athanor-<ns>" stays WARN below; the
    # (?<!athanor-) lookbehind keeps this BLOCK from reclassifying the pointer's
    # dotted forms. Fragment-built so this file holds no verbatim marker and does
    # not self-trip its own committed-tree scan.
    ("internal Kairos namespace", r"(?<!athanor-)" + "kai" + r"ros\.[A-Za-z_]"),
    ("confidential customer name", r"[Nn][Vv][Ii][Dd][Ii][Aa]"),
    ("confidential customer name", r"[Aa][Nn][Nn][Aa][Pp][Uu][Rr][Nn][Aa]"),
    ("GitHub token", r"gh[posru]_[A-Za-z0-9]{20,}"),
    ("GitHub fine-grained PAT", r"github_pat_[A-Za-z0-9_]{20,}"),
    ("Slack token", r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    ("AWS access key id", r"AKIA[0-9A-Z]{16}"),
    ("Anthropic API key", r"sk-ant-[A-Za-z0-9_-]{20,}"),
    ("OpenAI API key", r"sk-[A-Za-z0-9]{20,}"),
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
BLOCK_SCOPED: list[tuple[str, str]] = [
    ("home directory path", "/ho" + r"me/[A-Za-z0-9._-]+"),
    ("macOS home path", "/Use" + r"rs/[A-Za-z0-9._-]+"),
    ("tmp / tool-cache path", "/t" + r"mp/[A-Za-z0-9._/-]+"),
]
# Paths WE author on these forks; ambiguous host-path scanning is scoped to these.
OUR_ADDED_PREFIXES: tuple[str, ...] = (
    "athanor/",
    "athanor_artifacts/",
    "generated_rtl_capture/",
    "docs/customer/",
    "README.md",
)

# --- WARN tier: (label, extended-regex, exclude-regex-or-None). Never blocks.
WARN_PATTERNS: list[tuple[str, str, str | None]] = [
    # Case-insensitive + hyphen-optional (owner ruling: stays WARN): a producer
    # that emits "ath2852" (lowercase, no hyphen -- the natural machine form in a
    # schema/module segment) evaded the old case+hyphen-pinned "ATH-[0-9]{4}". The
    # leading \b keeps it off in-word digits like "datapath2960".
    ("internal Linear ticket id", r"(?i)\b" + "ath" + r"-?[0-9]{4}", None),
    # The private-repo pointer is WARN, but the internal ops-repo name is BLOCK;
    # exclude the ops-repo hits here so they are not double-reported as a warn.
    ("private Kairos-repo pointer", "athanor-" + "kairos", "athanor-" + "kairos-runall"),
]


class GateError(RuntimeError):
    """The gate could not run (distinct from a leak verdict)."""


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _repo_root(start: Path) -> Path:
    proc = _git(["rev-parse", "--show-toplevel"], start)
    if proc.returncode != 0:
        raise GateError(f"not a git repository at {start}: {proc.stderr.strip()}")
    return Path(proc.stdout.strip())


# Genuine-binary asset extensions are skipped (a credential in a compiled asset
# is far-fetched and scanning them yields garbage matches). Skips are REPORTED,
# never silent -- text logs (*.pinned.log) are NOT skipped and are fully scanned.
BINARY_ASSET_EXT = frozenset(
    (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".zip", ".gz", ".tgz",
     ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".so", ".o", ".a", ".bin")
)


def _committed_paths(ref: str, root: Path) -> list[str]:
    """All file paths tracked at ``ref`` (committed tree; untracked excluded)."""
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", ref],
        cwd=root, capture_output=True,
    )
    if proc.returncode != 0:
        raise GateError(f"git ls-tree failed at {ref}: {proc.stderr.decode(errors='replace').strip()}")
    return [p.decode("utf-8", "surrogateescape") for p in proc.stdout.split(b"\0") if p]


def _committed_bytes(ref: str, path: str, root: Path) -> bytes:
    """The committed bytes of ``path`` at ``ref`` (never the working tree)."""
    proc = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=root, capture_output=True)
    if proc.returncode != 0:
        raise GateError(f"git show failed for {path} at {ref}: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


def _scan_committed(ref: str, root: Path) -> tuple[list[str], list[str], list[str]]:
    """Byte-scan every committed file. Returns (block, warn, skipped_binaries).

    Scans BYTES rather than ``git grep`` so files marked ``binary`` in
    ``.gitattributes`` -- notably the pinned tool logs, the likeliest place a
    real credential leaks -- are searched too; ``git grep -I`` would skip them.
    """
    always_res = [(label, re.compile(pat.encode())) for label, pat in BLOCK_ALWAYS]
    scoped_res = [(label, re.compile(pat.encode())) for label, pat in BLOCK_SCOPED]
    warn_res = [
        (label, re.compile(pat.encode()), (re.compile(ex.encode()) if ex else None))
        for label, pat, ex in WARN_PATTERNS
    ]
    block: list[str] = []
    warn: list[str] = []
    skipped: list[str] = []
    for path in _committed_paths(ref, root):
        dot = path.rfind(".")
        ext = path[dot:].lower() if dot >= 0 else ""
        data = _committed_bytes(ref, path, root)
        if ext in BINARY_ASSET_EXT or b"\x00" in data:
            skipped.append(path)
            continue
        # Ambiguous host-path patterns fire only in files WE author; upstream's
        # own host paths (its .circleci etc.) are public-upstream content.
        in_our_scope = path.startswith(OUR_ADDED_PREFIXES)
        block_res = always_res + scoped_res if in_our_scope else always_res
        for lineno, line in enumerate(data.split(b"\n"), 1):
            shown = line.decode("utf-8", "replace").strip()[:200]
            for label, rx in block_res:
                if rx.search(line):
                    block.append(f"[{label}] {path}:{lineno}: {shown}")
            for label, rx, ex in warn_res:
                if rx.search(line) and not (ex and ex.search(line)):
                    warn.append(f"[{label}] {path}:{lineno}: {shown}")
    return block, warn, skipped


def _run_receipt_verifier(root: Path) -> list[str]:
    """Run the package receipt verifier; fail-closed if absent/errored."""
    verifier = root / "athanor" / "verify_public_receipts.py"
    if not verifier.is_file():
        return [f"receipt verifier missing at {verifier.relative_to(root)} (fail-closed)"]
    proc = subprocess.run(
        [sys.executable, str(verifier)], cwd=root, capture_output=True, text=True
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        return [f"receipt verifier failed (rc={proc.returncode}): {detail}"]
    return []


def run_gate(ref: str = "HEAD", start: Path | None = None) -> tuple[list[str], list[str], list[str]]:
    """Return (block, warn, skipped_binaries). Raises GateError if it cannot run."""
    root = _repo_root(start or Path.cwd())
    block, warn, skipped = _scan_committed(ref, root)
    block.extend(_run_receipt_verifier(root))
    return block, warn, skipped


def scan_text(text: str, source: str = "pr-text") -> list[str]:
    """Run the ALWAYS-block patterns over arbitrary public text -- a PR body,
    review comment, or issue comment. These are public surfaces on a public fork
    that the committed-tree scan cannot see (they are GitHub metadata, not files),
    so an internal build-path or a token in a PR body is public + invisible to the
    file gate (the #14 body-leak class, ATH-2960).

    Reuses BLOCK_ALWAYS as the SINGLE source of truth so the text surface and the
    committed-tree surface can never drift. The BLOCK_SCOPED host-path patterns
    are intentionally NOT applied to prose (a bare home-directory path in a
    sentence is not an unambiguous leak), but our internal markers + secret tokens
    always are. (No verbatim forbidden literal appears in this docstring so the
    gate does not self-trip on its own source.)
    """
    res = [(label, re.compile(pat)) for label, pat in BLOCK_ALWAYS]
    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for label, rx in res:
            if rx.search(line):
                findings.append(f"[{label}] {source}:{lineno}: {line.strip()[:200]}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ATH-2960 fork export-safety gate")
    parser.add_argument("--ref", default="HEAD", help="committed ref to scan (default HEAD)")
    parser.add_argument(
        "--warn-limit", type=int, default=40, help="max WARN lines to print (0 = all)"
    )
    parser.add_argument(
        "--scan-text",
        action="store_true",
        help="scan stdin (a PR/issue/review body) for BLOCK_ALWAYS internal markers "
        "+ secrets; exit 1 on a hit. Public-text surface companion to the file scan.",
    )
    args = parser.parse_args(argv)

    # PR bodies / review + issue comments are public surfaces on a public fork that
    # the committed-tree scan cannot see. Scan them with the SAME BLOCK_ALWAYS set.
    if args.scan_text:
        # Any failure to READ the text is a TOOL-ERROR (exit 2, legible
        # inconclusive), never a verdict (exit 1) or a clean pass (exit 0).
        # A closed/absent stdin makes sys.stdin None -> .read() raises
        # AttributeError (not OSError), and read-on-closed raises ValueError;
        # collapse all of these to the tool-error code so a broken input can
        # never masquerade as "leak found" or "clean".
        if sys.stdin is None:
            print("GATE-ERROR: no stdin available for --scan-text", file=sys.stderr)
            return 2
        try:
            text = sys.stdin.read()
        except (OSError, ValueError, AttributeError) as exc:
            print(f"GATE-ERROR: could not read text from stdin: {exc}", file=sys.stderr)
            return 2
        findings = scan_text(text)
        if findings:
            print(
                f"\nFAIL: {len(findings)} BLOCK-tier leak(s) in the PR/issue/review text:",
                file=sys.stderr,
            )
            for f in findings:
                print(f"  block: {f}", file=sys.stderr)
            print(
                "\nInternal markers/secrets are public on a public fork's PR page too "
                "-- scrub the PR body / comments.",
                file=sys.stderr,
            )
            return 1
        print("OK: PR/issue/review text clean (0 BLOCK-tier leaks).")
        return 0

    try:
        block, warn, skipped = run_gate(ref=args.ref)
    except GateError as exc:
        print(f"GATE-ERROR: {exc}", file=sys.stderr)
        return 2

    if skipped:
        print(f"INFO: {len(skipped)} genuine-binary file(s) not byte-scanned: {', '.join(skipped)}")

    if warn:
        print(f"WARN: {len(warn)} conscious-choice metadata finding(s) at {args.ref}:")
        shown = warn if args.warn_limit == 0 else warn[: args.warn_limit]
        for line in shown:
            print(f"  warn: {line}")
        if len(shown) < len(warn):
            print(f"  ... {len(warn) - len(shown)} more (raise --warn-limit to see all)")

    if block:
        print(
            f"\nFAIL: {len(block)} BLOCK-tier export-safety leak(s) at {args.ref}:",
            file=sys.stderr,
        )
        for line in block:
            print(f"  block: {line}", file=sys.stderr)
        print(
            "\nThese are hard-safety leaks on a PUBLIC fork. Remove them from the "
            "committed tree (do not commit generated *.replay.log; they belong in "
            "an ignored output dir).",
            file=sys.stderr,
        )
        return 1

    print(f"\nOK: export-safety gate clean at {args.ref} (0 BLOCK; {len(warn)} WARN).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
