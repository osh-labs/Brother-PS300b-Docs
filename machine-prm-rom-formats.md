# Machine definitions: `.PRM`, `MachineList.ml`, and `.ROM` / `.bin`

> Status: `.PRM` field map **[STRONG]**; machine-enumeration mechanism
> **[STRONG]**; ROM image internals **[HYPOTHESIS]**.

This is the document most relevant to *"can PS-300B be updated to support
machines newer than the ones it ships with?"* Short answer: **the machine list is
data-driven — each machine is one `.PRM` file in the `Machine\` folder, which the
app enumerates directly (no `MachineList.ml` edit needed). Cloning/retargeting an
existing entry is feasible and demonstrated here for the KE-430HS (§4.0);
inventing support for a machine whose firmware protocol the software does not
already implement is not.**

---

## 1. `.PRM` — machine parameter file

One file per machine model in the `Machine\` folder. The filename is the model
(e.g. `KE430F.PRM`, `KE430D.PRM`, `B430EMK2(KE430B KE430C).PRM`). Parentheses in
the filename list the equivalent/rebadged models that share the definition.

### 1.1 KE430-class layout (132 bytes) — single needle  [STRONG]

Annotated from `KE430F.PRM` / `KE430D.PRM`:

```
off  bytes              meaning
0x00 "KE430F\0\0\0\0"   model name, **fixed 10-byte field** (0x00–0x09).
        ^ Names ≤9 chars are NUL-padded; a 10-char name fills the field with NO
          terminator and still works (e.g. shipped `BAS342GXL_sp.PRM` stores
          "BAS342GXL_" across all 10 bytes). Names >10 chars are truncated.
          The first numeric field is ALWAYS at 0x0A regardless of name length.
0x0A c8 00              200        (0x00C8 — a default, appears across models)
0x0C 20 03             800        max X span? (steps)  [KE430 field is 40 mm = 800 steps]
0x0E c8 00             200
0x10 01 00             1          flag
0x12 29 00             41         (0x29)
0x14 88 13 00 00       5000       (0x1388)  max sewing speed (spm)  [HYPOTHESIS]
        ^ KE430D=0x4E20(20000), KE430F=0x5000(20480) — the only diff between D and F
0x1C cd cc 4c 3d       0.05  (float32)  SCALE FACTOR: machine step -> mm
0x20 cd cc 4c 3d       0.05  (float32)
0x24 33 33 4b 41       12.7  (float32)  (= 0.5 inch? a fixed geometry constant)
0x28 cd cc 4c 3d       0.05  (float32)
0x2C cd cc 4c 3d       0.05  (float32)
0x30 00 00 00 00
0x34 00 00 00 00
0x38 70 fe ff ff      -400  (int32)   field minX (steps)  ┐  ±400 × ±300 steps
0x3C d4 fe ff ff      -300  (int32)   field minY          │  × 0.05 mm
0x40 90 01 00 00       400  (int32)   field maxX          │  = 40 mm × 30 mm
0x44 2c 01 00 00       300  (int32)   field maxY          ┘  (the KE430 sewing area)
0x48 04 00            ...
0x4A "D:\BROTHER\ISM\ISMDA00\ISMS0***.SEW\0"
        ^ OUTPUT PATH TEMPLATE: where exported .sew files are written and how
          they are named. "***" is replaced by the 3-digit pattern number, so
          patterns become ISMS0200.SEW, ISMS0201.SEW, ... in folder ISMDA00.
```

Key takeaways:
- **Scale factor `0.05`** ties machine steps to millimetres and matches the
  `.sew` unit. `B430E` (older) uses `0.1` instead.
- **Field bounds** are the hard clip region the exporter enforces ("This data
  exceeds frame area").
- **Output path template** drives the `ISMDA00\ISMS0NNN.SEW` naming you see on
  disk. Different machines use different `ISMD?00` subfolders (the bartack
  example lives in `ISMDA00`; the bundled demo patterns in `ISMDB00`).

### 1.2 Older / smaller layout (108 bytes)  e.g. `B430E.PRM`, MK2 variants

Same name + field-bounds + scale idea but a shorter record and **no `.SEW` path
template** (these predate the ISM-folder export naming, or store the suffix
elsewhere). `B430EMK2(KE430B KE430C).PRM` has bounds `-150..150 / -50..150`
(steps) and scale `0.1`.

### 1.3 Extended layout (224 bytes) — multi-needle  e.g. `BAS752.PRM`

Adds a **needle-position table** after the common header: two interleaved lists
of int16 positions (`01 03 07 0B 0F 13 …` then `02 06 0A 0E …`) describing the
needle-bar offsets of a multi-needle bridge machine. Not relevant to KE430 but
documents why PRM sizes vary (108 / 116 / 132 / 136 / 224 bytes across the
folder).

> The PRM is a flat C `struct` dumped to disk; sizes vary because different
> machine classes use different trailing structures. The leading
> name+bounds+scale block is common to all.

---

## 2. Machine enumeration — the software scans `Machine\*.PRM`  [STRONG]

The exe builds the **"Machine Model Setting"** list by **enumerating the
`Machine\` folder with a `*.PRM` / `*.*` wildcard** (the `FindFirstFile`-style
strings `*.PRM`, `\*.*`, `Machine\` sit together in the binary). Evidence that
this is the live mechanism: **`MachineList.ml` is not present anywhere in this
install, yet `KE430F` and every other `.PRM` appear and work.** So:

> **To add a machine you simply drop a valid `.PRM` into `Machine\`.** No registry
> edit or list-file maintenance is required. (`MachineList.ml` is still referenced
> by the code — likely an optional cache / ordering file or used by the companion
> `SW1Win.exe` transfer utility — but is not needed to register a model.)

The app also touches the registry under
`HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SW1WinUS\`.
If a model doesn't appear after adding its `.PRM`, restart PS-300B (the folder is
scanned at startup / when the dialog opens).

---

## 3. `.ROM` + `.bin` — master pattern / firmware images  [HYPOTHESIS]

In `ROM File\` each machine has a pair:

- `MASTER_<model>_MN_<rev>.ROM` — an **86-byte descriptor**:
  `00 00` + model name (ASCII) + `… 00 10`/`00 12` flag near offset 0x0E. It
  *names/points to* the binary and carries a size/type flag.
- `Master_<model>_MN_<rev>.bin` — the actual **ROM image** (64 KB / 128 KB /
  256 KB — i.e. 27512 / 27010 / 27020-class EPROM sizes). Begins with
  `00 00 10 00 FF FF … <model name> …` then a table of `00 00 00 F4 …` entries
  (a pattern/offset table padded with `F4`).

These are the images written to a physical EPROM via the **ROM writer** path in
the import/export DLL ("Set right size ROM chip", "PROM write error", "ROM
version error", "Machine model mismatch, can not export to the ROM file"). They
are the machine's **built-in pattern set / firmware**, distinct from the
user-pattern `.sew` files. The `mau may.BIN` / `mau may.ROM` pair is a
user-supplied (non-Brother-named) image dropped into the same folder.

Decoding the `.bin` pattern table is a separate effort; the per-pattern stitch
data inside is expected to use the same packed encoding as `.sew` chunk `0x0004`.

---

## 4. Adding / retargeting a machine — what's realistic

### 4.0 Worked example: adding the **KE-430HS** (done)  [CONFIRMED build]

The **KE-430HS / KE-430HX** (service manual `docs/ke430hx.pdf`) is an electronic
direct-drive lockstitch bar tacker. Spec table (manual §1):

- **Normal sewing area = 40 × 30 mm** (note *2; optional `SB7777-001` set gives
  50 × 40). → matches the KE430F field exactly (`±400 × ±300` steps × 0.05 mm).
- Max sewing speed 2,800 sti/min; **data media = USB memory**; loads `.sew`.

Because the area, scale, and output path are identical to `KE430F` (which is
already in successful use for this machine), the profile is a **name-only clone**:

```
Machine\KE430HS-05.PRM  =  KE430F.PRM  with bytes 0x00–0x09 set to "KE430HS-05"
```

"KE430HS-05" is exactly 10 characters → it fills the fixed 10-byte name field
perfectly (same technique as the shipped `BAS342GXL_sp.PRM`). Every other byte is
identical to `KE430F.PRM`, so PS-300B generates **byte-identical `.sew` output**
to the known-good KE430F profile — just under a correctly-labelled model. Built
with `analysis/sew_write.py`'s sibling one-liner; verified only bytes 5–9 differ
from `KE430F.PRM`. Drop it in `Machine\`, restart PS-300B, pick it in *Machine
Model Setting*.

> Notes: (a) the PRM "speed" words (0x14/0x18) are **not** the 2,800-spm machine
> limit (they read 5000/20480 in KE430F and are a software-side value); leave them
> as-is since KE430F works. (b) For the optional **50 × 40** area, instead set the
> bounds to `±500 / ±400` steps (int32 at 0x38–0x44: minX −500, minY −400, maxX
> 500, maxY 400) — but only if you fit the optional sewing-area set on the
> machine, else the wider patterns will exceed the physical frame.

### 4.1 What works generally: cloning an existing, supported model
- The KE430 family (KE430B/C/D/F/HX/HS) shares the ISM `.sew` dialect. To target a
  variant, copy the closest `.PRM`, rename the file, set the 10-byte model-name
  field, and adjust field bounds / scale / output template as needed. The folder
  is scanned directly — **no `MachineList.ml` edit required** (§2).

### 4.2 What partly works: a newer machine that speaks an existing dialect
- If a newer head accepts the **same ISM `.sew` format** (BIL container +
  the stitch encoding in [sew-format.md](sew-format.md)) on the same media, a
  new `.PRM` with correct bounds/scale may be enough to export usable files.
  This must be validated on hardware — the firmware may have added codes or
  changed the media protocol.

### 4.3 What does not work from data alone
- A machine that uses a **different transfer protocol or file format** than the
  ones the import/export DLL implements (floppy/FD300, serial/COM, ROM writer)
  cannot be supported by adding a `.PRM`; the protocol lives in compiled code
  (`PS300BMachineImportExportENU.dll`), not in the data files. Supporting it
  would require patching/replacing that DLL.

### 4.4 The higher-leverage option
Because the `.sew` format is now decoded, the most future-proof path is **not**
to extend the 2002 app at all, but to write a small standalone converter that
emits `.sew` (and reads `.emb`) directly — then you are free of the original
software's machine list entirely and can target any head that loads ISM `.sew`
files. See the "writing a `.sew`" recipe in [sew-format.md](sew-format.md).

---

## 5. Other capabilities worth knowing (from the binaries)

- **Import:** BMP/JPG (image → trace to outline), DXF (vector), EMB.
- **Export:** EMB, DXF, and machine `.sew`/`.CUT`/ROM.
- **Transfer/media:** floppy (drive A) via the **FD300** unit, **serial/COM**
  (baud-rate settings present), and **EPROM** via a ROM writer.
- **Other machine file types** the DLL handles: `.CUT` (cutter data, e.g.
  `B800E.CUT`), `.ALL` (full backup set), `.BAS` (`bas0*.sew` for BAS machines).
- **Editor codes** that can be inserted into sewing data: Thread Tension /
  Two-Step / Digital Tension (≤99), Change Speed (Speed 0–7), Trim, Cutter On,
  Feed / Manual Feed, Split Needle Up/Low, Stop Needle Upper/Lower, Second /
  Machine Original Point.
- **Parametric generators** (in `PatternGenerater*.dll`): straight bartack,
  back-tack, eyelets (round/radial/rectangular/tapered), with ~68 named
  parameters (lengths, pitches, widths, tack counts, underlay, 2-cycle sewing,
  tension timing). This is how the bartack example was created — by parameters,
  not by drawing.
