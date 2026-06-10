# Brother PS-300B — Reverse-Engineering Notes

Research notebook for the Brother **PS-300B** programmable-stitch / ISM
(Individual Stitch Memory) pattern software and its file formats, with the goal
of being able to **read stitch data out of** and **write valid stitch patterns
into** these files — independent of the original (Windows-only, 2002-era)
application.

Primary machine of interest: **KE430 series** (KE430B/C/D/F, the bartack /
programmable-tacking head). Sewing field for KE430 = **40 mm × 30 mm**.

## Documents in this folder

| File | Contents |
|------|----------|
| [software-overview.md](software-overview.md) | What PS-300B is, how it works, its data model, the install tree, the import/export pipeline, supported machines, and how to add new ones. |
| [sew-format.md](sew-format.md) | The `.sew` machine file (the file uploaded to the machine). Container + **fully-decoded stitch encoding**. This is the most important format for producing machine-ready patterns. |
| [emb-format.md](emb-format.md) | The `.emb` PS-300B native project file (editable outline + generated sewing data + preview). |
| [machine-prm-rom-formats.md](machine-prm-rom-formats.md) | `.PRM` machine-definition files, `.ROM`/`.bin` firmware images, how machines are enumerated, and a worked recipe for adding a machine (incl. the KE430HS-05 profile). |
| [pattern-generator.md](pattern-generator.md) | The parametric design engine (`PatternGenerater*.dll`): interface, pattern catalogue, and a detailed breakdown of **`_BARTACK(800Series)`**. |
| [analysis/](analysis/) | Python tooling used to derive everything here. Re-runnable. |

## Confidence legend

Throughout the docs:

- **[CONFIRMED]** — verified by cross-checking independent files (e.g. decoded
  stitch path bounding-box matches the file's own stored bounding-box), or read
  directly from unambiguous binary structure.
- **[STRONG]** — consistent with all observed data and with strings pulled from
  the codec DLLs, but not yet bit-for-bit round-tripped.
- **[HYPOTHESIS]** — plausible, partially supported, needs more samples.

## The Rosetta stones

Two matched `.emb`/`.sew` pairs drive the reverse engineering:

| `.emb` (project) | `.sew` (machine) | pattern | what it pins down |
|---|---|---|---|
| `Examples/bartack.emb` | `Examples/ISMS0200.sew` | single satin bartack | stitch encoding, units, container |
| `Examples/QS Plus Tack.emb` | `Examples/ISMS0201.sew` | "plus" tack: 2 end-tacks + center bar | multi-block structure, trim, sew-start, EMBDATA segment/code format |
| `Examples/feedonly.emb` | `Examples/ISMS0202.sew` | feed-only: (0,0)→(5,5)→(-5,5) mm | feed encoding (unit, sign, axis) + the editor↔machine Y-flip |
| `Examples/codesonly.emb` | `Examples/ISMS0203.sew` | 7 inserted codes on a stitch line | **data-code opcodes: split / option / deceleration** |

Cross-decoding the first pair pinned down the geometry and the unit
relationship:

```
.emb coordinate units  =  1/400 mm  (0.0025 mm)
.sew / machine units    =  1/20  mm  (0.05  mm)   <-- matches KE430 PRM scale 0.05
ratio  emb:sew          =  20 : 1
```

The decoded `.sew` bartack path spans **785 × 80** machine units, which **exactly
matches** the bounding box stored inside the same file (chunk type `0x0003`).
That equality is the main proof the stitch codec below is correct.

## Current research status (2026-06-09, updated with QS Plus Tack sample)

- `.sew` **container**: fully mapped. [CONFIRMED]
- `.sew` **in-block stitch encoding** (needle points, split-needle flag, axis,
  sign, magnitude): fully decoded and verified. [CONFIRMED]
- `.sew` **control opcodes** `0xFF` EOF, `0xFD 00` **thread trim**, `0xF4`
  **sew-start**: confirmed via the QS Plus Tack + a controlled trim edit. [CONFIRMED]
- `.sew` **FEED records**: encoding confirmed via the controlled feed-only export
  (`ISMS0202.sew`) — `0x00–0x3F` range, same axis(0x08)/sign(0x04) bits and the
  same **1-step (0.05 mm) magnitude** as stitches; deltas in editor coords.
  Earlier "coarse ×4 unit" guess was wrong. [CONFIRMED]
- **Editor↔machine Y-flip** confirmed: deltas are editor coords (Y up); the
  chunk-0x0003 bbox is machine coords (Y negated). [CONFIRMED]
- **`.sew` writer works**: `analysis/sew_write.py` reproduces a genuine export
  (`ISMS0202.sew`) **byte-for-byte except one checksum word**. [CONFIRMED]
- **`.sew` data codes** (controlled exports `ISMS0203.sew`): `FE`=split-needle
  (arg low/high), `FC`=option (arg bitmask opt1/2/3), `FB`=deceleration level
  (arg 1–7), **`FD 00`=thread trim**; deceleration-*off* is the default and emits
  no code. [CONFIRMED]
- Decoder rule: classify `(cmd & 0xF0)==0xF0` as a code FIRST (these have 0x40
  set), then `0x40`=stitch, else feed. [CONFIRMED]
- Residual (minor): the two per-file checksum words; tension/speed/cutter codes;
  and the `0x10/0x02` feed sub-mode flags. [open]
- `.emb`: header, machine field, embedded paths, preview bitmap mapped; the
  **EMBDATA segment format** (`0E 02 00 tt` marker + fields + 2-byte code word +
  absolute int16 XY) is decoded and cross-validated against the matching `.sew`
  bounding box. Per-code field semantics partial. [STRONG]
- `.PRM` machine files and `.ROM`/`.bin` images: mapped. Adding a machine =
  dropping a `.PRM` in `Machine\` (the app scans the folder; no `MachineList.ml`
  edit needed). **`KE430HS-05.PRM` built** as a name-only clone of KE430F. [CONFIRMED]

## How to reproduce / continue

```
python docs/analysis/sew_parse.py          # dump .sew chunk structure
python docs/analysis/sew_decode_verify.py  # decode single-block stitches, check vs stored bbox
python docs/analysis/sew_decode2.py        # multi-block decoder: feeds, trim, sew-start, EOF
python docs/analysis/emb_parse.py          # explore .emb coordinate runs (bartack)
python docs/analysis/emb_section.py        # linear dump of an .emb sewing section
python docs/analysis/emb_extract.py        # robust .emb segment/coordinate extractor (ground truth)
python docs/analysis/codes_correlate.py    # align .emb code records to .sew code bytes by X
python docs/analysis/sew_write.py          # .sew WRITER (stitches/feeds/codes); byte-identical proof
python docs/analysis/strings.py <file> [regex]   # ASCII+UTF16 strings
```

Full string dumps of the key binaries are cached in `analysis/strings_*.txt`.
