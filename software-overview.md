# PS-300B software overview

> Status: **[STRONG]** — assembled from the install tree, the embedded strings of
> `PS300B.exe` and its DLLs, the `INSTALL.DAT`, and the bundled help/manual.

## 1. What it is

**Brother PS-300B** is a Windows desktop **programming / digitising application
for Brother industrial "ISM" (Individual Stitch Memory) sewing heads** — the
programmable bartack, button-sew, and short-cycle pattern machines such as the
**KE430 series**, plus BAS / ZE / HE / B-series heads.

It is the PC half of a workflow whose machine half is a single-pattern sewing
head: you design a stitch pattern on the PC, export it to a machine file
(`.sew`), move that file to the machine (floppy/serial/EPROM), and sew it.

- Product: **PS-300B**, version **4.3** (per `INSTALL.DAT`), © **Brother
  Industries, Ltd.** The bundled `PS300B.exe` here is dated **2014** (a late
  build); supporting DLLs span 2004–2014.
- Installs to `…\Program Files\brother\PS-300B\`.
- Localised into **ENU/CHS/FRA/JPN** (English/Chinese/French/Japanese) via
  per-language DLLs and `.chm` help files.
- A companion transfer tool, **SW1Win.exe / "SW1WinUS"**, is referenced for some
  media operations.

## 2. The three-layer data model

Understanding this is the key to the file formats:

```
   OUTLINE  ──(generate stitch)──►  SEWING DATA  ──(export via .PRM)──►  .sew
   (vector shapes,                  (needle points +                    (machine
    editable, parametric)            codes, EMBDATA)                      file)
        └──────────────── both stored in the .emb project ─────────────┘
```

1. **Outline** — editable geometry: straight lines, polylines, arcs, and
   **parametric objects** (bartack, back-tack, eyelets — round/radial/rectangular/
   tapered). You can also import an outline by tracing a **BMP/JPG** image or
   loading a **DXF**. Editing the outline and re-running "generate stitch"
   re-creates the stitches.
2. **Sewing data** — the concrete list of **needle points** plus inserted
   **codes** (tension, speed, trim, feed, split-needle, stops, second origin).
   This is what actually sews. Editable point-by-point ("Select Punch Point",
   "Change stitch to feed", "Insert/Delete code(s)").
3. **Machine file** — the exported **`.sew`**, down-converted from the high-res
   sewing data (1/400 mm) to machine steps (1/20 mm) and packed for the target
   machine selected via its **`.PRM`**.

`.emb` stores layers 1+2 (the project); `.sew` is layer 3 (machine output). See
[emb-format.md](emb-format.md) and [sew-format.md](sew-format.md).

## 3. Typical workflow

1. **Select machine model** ("Machine Model Setting") — picks a `.PRM` from
   `Machine\`, which sets the sewing-field size, scale, speed limits, and the
   `.sew` output folder/name template. The chosen model name is saved into the
   `.emb` (e.g. `KE430F`).
2. **Create the pattern** — draw/parametric-generate an outline, or trace an
   image / import DXF; generate stitches; tune with codes (tension, speed,
   trims, feeds).
3. **Check** against the field area and pitch/stitch limits (the app warns on
   over-frame and over-pitch).
4. **Export to machine media** ("Output sewing data to machine media" / Import =
   "Input sewing data from machine media") — writes `ISMD?00\ISMS0NNN.SEW` to
   floppy (FD300), serial, or an EPROM via the ROM writer.
5. Load on the machine and sew. The KE430 holds the pattern in its ISM.

## 4. Install tree (what each piece does)

| Item | Role |
|------|------|
| `PS300B.exe` | Main application (MFC, statically references the language + codec DLLs). |
| `PS300B<LANG>.dll` (ENU/CHS/FRA/JPN) | UI resources / localisation. |
| `PatternGenerater<LANG>.dll` | **Parametric stitch engine.** Exposes `StartPatternGenerater()` and `GetSewingData(header&, CArray<EMBDATA>&)`; turns bartack/eyelet/etc. parameters into sewing data. |
| `PS300BMachineImportExport<LANG>.dll` | **Machine I/O + `.sew` codec.** Reads/writes `.sew`/`.CUT`/`.ALL`/`.BAS`/ROM, talks to floppy/FD300/serial/ROM-writer, enforces frame/pitch limits, reads `.PRM` and `MachineList.ml`. |
| `PS300B*.chm`, `ps300b.pdf` | Help (per language) and the 165-page PDF user manual (root). |
| `Machine\*.PRM` | Machine definitions (see [machine-prm-rom-formats.md](machine-prm-rom-formats.md)). |
| `ROM File\*.ROM` + `*.bin` | Master pattern / firmware EPROM images + descriptors. |
| `BROTHER\ISM\ISMD?00\ISMS0*.sew` | The on-disk machine-pattern library (export target & bundled samples). |
| `Examples\bartack.emb` + `Examples\ISMS0200.sew` | The same bartack as project + machine file — the reverse-engineering Rosetta stone. |
| `*.DLL` (ADVAPI32, COMCTL32, MFC42, MSVCRT, OLE*, …) | Bundled Win32/MFC runtime (2002–2004 vintage) so the app runs on a clean machine. |
| `INSTALL.DAT` | Installer manifest (EINSTALL 2.0): version 4.3, paths, copyright. |

## 5. Supported machines (from `Machine\` + exe strings)

- **KE430 family** (bartack/programmable tack): `KE430D`, `KE430F`,
  `B430E`/`B430EMK2` (= KE430B/KE430C), `B431E`/`KE431…`, `B432E`, `B433E`,
  `B434E`, `B438E`/`BE438*`, `B448E`, `KE436B/C`, `B484EMK2`/`KE484C`.
- **BAS series** (programmable electronic pattern sewers): `BAS300G`, `BAS304(A)`,
  `BAS311*`, `BAS326*`, `BAS341*/342*/343E`, `BAS34XG`, `BAS364/366/370/375(E)`,
  `BAS705`, `BAS752/754/755/760/761/7610`.
- **Z / ZE / HE / B-8xx**: `Z8550A/8560A`, `ZE855A/856A`, `ZE857x/858x`,
  `B800E`/`HE800A`, `B855E/856E`.

(Filenames with parentheses cover multiple rebadged equivalents.) Newer machines
than these are **not** listed; see the "adding machines" analysis in
[machine-prm-rom-formats.md §4](machine-prm-rom-formats.md).

## 6. Practical conclusions for this project

- **Extracting stitch data**: solved for `.sew` (geometry fully decoded) and
  largely solved for `.emb` (absolute coordinates decode directly). You can pull
  needle paths out of any sample today with the scripts in `analysis/`.
- **Producing patterns**: the `.sew` container + stitch encoding are simple
  enough to write directly; the remaining gap is the feed/code preamble for
  multi-section patterns. Until that's closed, the reliable route is to author
  geometry and round-trip the final file through the original exporter, or to
  validate hand-written files on the KE430 before production.
- **Targeting the KE430**: it is a first-class supported model; field = 40×30 mm,
  step = 0.05 mm, output as `BROTHER\ISM\ISMDA00\ISMS0NNN.SEW`.
- **Extending to new machines**: data-driven for already-supported dialects
  (clone a `.PRM`), but new transfer protocols/formats require touching the
  compiled import/export DLL. The cleaner long-term play is a standalone
  `.emb`/`.sew` converter (now feasible) rather than extending the 2002 app.

## 7. Open questions / next steps

- Close the `.sew` **feed/code** map (trim, speed, tension, inter-block feed)
  by exporting single-feature test patterns and diffing — see
  [sew-format.md §3.3](sew-format.md).
- Pin the exact **`EMBDATA`** record layout the same way (see
  [emb-format.md §3](emb-format.md)).
- Determine whether the `.sew` header **uid/checksum** (`+0x0A`) is validated by
  the machine; if so, derive its algorithm.
- Optionally decode the **`ROM File\*.bin`** master-pattern tables.

(Resolved: machine registration is just `Machine\*.PRM` enumeration — no
`MachineList.ml` needed; a `KE430HS-05.PRM` profile has been added — see
[machine-prm-rom-formats.md §4.0](machine-prm-rom-formats.md).)
