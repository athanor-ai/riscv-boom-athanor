# Athanor BOOM: Generator-Capture Track

This fork is the Athanor public surface for BOOM, a generator-first
out-of-order 64-bit RISC-V core. Unlike OpenC910, BOOM does not expose a single
direct RTL tree as the proof subject; the first required artifact is a pinned
generated-RTL/config package.

How the work divides (the same across every Athanor fork): the AI generates the
optimization proposals and scaffolding; open, formal tools generate the verdicts
(Yosys equivalence, OpenSTA timing/power, Lean invariants); and Kairos supplies
the contract, routing, binding, ledger, and claim discipline. Kairos does not
replace the prover or the model -- it binds an exact candidate to its
measurements and proofs and refuses to promote anything that skips the bar. The
promotion rule below is that discipline; no BOOM row is promoted until it clears
every step.

## Current Status

| Question | Current answer |
| --- | --- |
| Is there a promoted BOOM optimization? | No. No BOOM optimization row is promoted yet. |
| What is the first receipt? | Generated RTL/config capture: pinned Chipyard hash, generator command, generated Verilog hashes, and replay instructions. |
| What will a promoted row require? | Same-candidate selected area, OpenSTA max data-arrival, OpenSTA estimated power, scoped proof, proof mutant, and independent replay. |
| Where will receipts live? | Under [`athanor_artifacts/`](athanor_artifacts/) once capture and module packets land. |

## Promotion Rule

Future BOOM rows follow the same bar as OpenC910:

1. exact generated RTL/config provenance,
2. area/timing/OpenSTA estimated-power measurements on the same mapped candidate
   netlist,
3. same-state equivalence or visible-output/state-relation proof with stated
   reset/environment assumptions,
4. a proof negative-control that fails the same proof,
5. hash-bound replay plus independent non-author review.

Lean obligations should be generated for state-relation or composition gaps:
`reset_establishes`, `transition_preserves`, and
`relation_implies_visible_outputs`, with a weakened-relation or theorem mutant
that fails.

## Non-Claims

This fork does not currently claim a BOOM optimization, whole BOOM proof, ISA
correctness, memory consistency, speculation recovery, signoff/workload power,
or whole-chip authority. Until generated RTL/config is pinned, BOOM is a
capture track, not a proof-packet track.

<details>
<summary>Upstream BOOM README</summary>

![](docs/figures/evolution.png)

The Berkeley Out-of-Order RISC-V Processor [![CircleCI](https://circleci.com/gh/riscv-boom/riscv-boom.svg?style=svg)](https://circleci.com/gh/riscv-boom/riscv-boom)
====================================================================================================================================================================

The Berkeley Out-of-Order Machine (BOOM) is a synthesizable and parameterizable open source RV64GC RISC-V core written in the [Chisel](https://chisel.eecs.berkeley.edu/) hardware construction language.
Created at the University of California,
Berkeley in the [Berkeley Architecture Research](https://bar.eecs.berkeley.edu/) group, its focus is to create a high performance, synthesizable, and parameterizable core for architecture research.
The current version of the BOOM microarchitecture ([SonicBOOM, or BOOMv3](https://carrv.github.io/2020/papers/CARRV2020_paper_15_Zhao.pdf)) is performance competitive with commercial high-performance out-of-order cores, achieving 6.2 CoreMarks/MHz.

![](docs/figures/uarch.png)


Feature | BOOM
:-- | :--
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

</details>
