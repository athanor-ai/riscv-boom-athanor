# Athanor BOOM: Verifiable Out-of-Order RISC-V Optimization

This fork is the Athanor campaign surface for BOOM, a generator-first
out-of-order 64-bit RISC-V core. It exists alongside
[`openc910-athanor`](https://github.com/athanor-ai/openc910-athanor): OpenC910
is the direct-RTL track, while BOOM requires generated RTL/config capture before
the same replay-packet discipline can apply.

The operating rule for this fork is receipt-first. Results land on `master` with
explicit links to artifact packages, replay commands, hashes, and proof/test
logs. A row is not a win until its exact proof subject is stated and replayable.

## Athanor Results

| Target | Status | Optimization / PPA | Proof, test, or simulation receipt | Receipt location |
| --- | --- | --- | --- | --- |
| BOOM generated RTL/config capture | In progress | No optimization claimed | Blocking receipt: this repo is generator-first; first packet requires a pinned Chipyard hash/config, generated Verilog, and replayable synthesis/proof commands | Pending `athanor_artifacts/generated_rtl_capture/` |
| First BOOM module-local packet | Pending | No optimization claimed | Candidate target will be selected after generated RTL is pinned; expected proof bar is selected PPA plus same-state equivalence or visible-output relation proof with biting mutant | Pending |

## BOOM Campaign Plan

1. Capture a reproducible BOOM generated-RTL configuration using the tracked
   `CHIPYARD.hash` and an explicit generator command.
2. Package generated RTL provenance under `athanor_artifacts/` with hashes and
   replay instructions.
3. Select a tractable module-local target from the generated RTL.
4. Run Kairos plus specialist agents for candidate generation, authoritative
   scoring, proof, adversarial QA, and campaign-learning records.
5. Promote only rows with exact receipt links in the table above.

## Non-Claims

This fork does not currently claim a BOOM optimization, whole BOOM proof, ISA
correctness, memory consistency, speculation recovery, or whole-chip authority.
Until generated RTL/config is pinned, BOOM is a generator-capture track, not a
proof-packet track.

## Upstream README

![](docs/figures/evolution.png)

The Berkeley Out-of-Order RISC-V Processor [![CircleCI](https://circleci.com/gh/riscv-boom/riscv-boom.svg?style=svg)](https://circleci.com/gh/riscv-boom/riscv-boom)
====================================================================================================================================================================

The Berkeley Out-of-Order Machine (BOOM) is a synthesizable and parameterizable open source RV64GC RISC-V core written in the [Chisel](https://chisel.eecs.berkeley.edu/) hardware construction language.
Created at the University of California,
Berkeley in the [Berkeley Architecture Research](https://bar.eecs.berkeley.edu/) group, its focus is to create a high performance, synthesizable, and parameterizable core for architecture research.
The current version of the BOOM microarchitecture ([SonicBOOM, or BOOMv3](https://carrv.github.io/2020/papers/CARRV2020_paper_15_Zhao.pdf)) is performance competitive with commercial high-performance out-of-order cores, achieving 6.2 CoreMarks/MHz.

![](docs/figures/uarch.png)


Feature | BOOM
--- | ---
ISA | RISC-V (RV64GCB)
Synthesizable |√
FPGA |√
Parameterized |√
IEEE 754 Floating Point |√
Atomics |√
Caches |√
Virtual Memory |√
Boots Linux |√
Runs SPEC |√
CoreMark/MHz |6.2


## IMPORTANT: Using BOOM
This repository is **NOT A SELF-RUNNING** repository. To instantiate a BOOM core, please use the
[Chipyard](https://github.com/ucb-bar/chipyard) SoC generator.

The current hash of Chipyard that works with this repository is located in the `CHIPYARD.hash`
file in the top level directory of this repository. This file is mainly used for CI purposes, since
Chipyard should follow the correct version of rocket-chip. For most users, you should be able to
clone Chipyard separately and follow the default Chipyard instructions (without having to use the `.hash` file).

While BOOM is primarily ASIC-optimized, it is also usable on FPGAs.
Chipyard provides infrastructure and documentation for deploying BOOM on AWS F1 FPGAs through FireSim.

## Documentation and Information

Please check out the BOOM website @ https://boom-core.org for the most up-to-date information.
It contains links to the mailing lists, documentation, design spec., publications and more!

If you use BOOMv3 in your published work, please cite BOOM as

```
@article{zhaosonicboom,
  title={SonicBOOM: The 3rd Generation Berkeley Out-of-Order Machine},
  author={Zhao, Jerry and Korpan, Ben and Gonzalez, Abraham and Asanovic, Krste},
  booktitle={Fourth Workshop on Computer Architecture Research with RISC-V},
  year={2020},
  month={May}
}
```

**Website:** (www.boom-core.org)

**Mailing List** (https://groups.google.com/forum/#!forum/riscv-boom)

## Disclaimer!

BOOM is a work-in-progress and remains in active development.

## Contributing

Please see [CONTRIB\_AND\_STYLE.md](/CONTRIB_AND_STYLE.md)
