# Athanor BOOM Artifacts

This directory holds Athanor-generated BOOM campaign receipts.

The first required package is `generated_rtl_capture/`, which must record:

1. BOOM fork commit and `CHIPYARD.hash`.
2. Chipyard/config command used to generate Verilog.
3. Generated RTL hashes.
4. Toolchain versions used for synthesis/proof attempts.
5. Replay commands that regenerate or verify the generated RTL package.

No optimization row should be added to the root README until its artifact
package carries the exact source, proof/test logs, replay commands, and hashes.
