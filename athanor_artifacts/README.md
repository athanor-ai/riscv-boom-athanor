# Athanor BOOM Artifacts

This directory holds Athanor-generated BOOM campaign receipts.

## Verification status

**Receipt verifier active — 0 customer-ready packets to validate yet.**

Every push runs `athanor/verify_public_receipts.py` (SHA256SUMS binding, replay
self-check, and receipt-to-log parsing) plus its always-run bite suite, so the
auditor bar is enforced from day one. BOOM is a capture-track fork: it has not
promoted any `customer_ready=true` packet, so today the verifier is a clean
no-op. The moment a packet lands, the same checks gate it — nothing ships
unverified.

The first required package is `generated_rtl_capture/`, which must record:

1. BOOM fork commit and `CHIPYARD.hash`.
2. Chipyard/config command used to generate Verilog.
3. Generated RTL hashes.
4. Toolchain versions used for synthesis/proof attempts.
5. Replay commands that regenerate or verify the generated RTL package.

No optimization row should be added to the root README until its artifact
package carries the exact source, proof/test logs, replay commands, and hashes.
