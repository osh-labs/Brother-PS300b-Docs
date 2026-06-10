# The `.emb` PS-300B project file format

> Status: header / machine field / embedded paths / preview / coordinate runs
> **[STRONG]**; exact `EMBDATA` record layout **[HYPOTHESIS]**.

`.emb` is PS-300B's **native document** ("PS300B Files (*.emb)"). It is what you
open and edit in the application. Unlike [`.sew`](sew-format.md) (a lean
machine-coordinate stream), `.emb` is an editor project: it stores the selected
**machine model**, editor/working **paths**, a small **preview bitmap**, and the
**sewing data** (needle points + codes) at high resolution, plus room for the
editable **outline** (the vector shapes that *generate* the stitches).

Reference sample: `Examples/bartack.emb` (3056 bytes) — the same bartack as
`Examples/ISMS0200.sew`.

---

## 1. Units

`.emb` needle coordinates are **absolute, signed 16-bit (X,Y)** in units of
**1/400 mm (0.0025 mm)** — i.e. **20× finer** than the `.sew`/machine step of
0.05 mm. To convert a needle point to machine steps: `step = emb / 20`. To mm:
`mm = emb / 400`.

(Derivation: the bartack satin spans 15700 emb units in X; the same pattern's
`.sew` bounding box spans 785 machine steps; 15700 / 785 = 20; 785 × 0.05 mm =
39.25 mm = 15700 / 400 mm.)

---

## 2. Overall layout (observed)  [STRONG]

The file is a fixed-ish header region, a reserved/zero gap, a small preview
bitmap, then the sewing-data section. Offsets below are from `bartack.emb`; the
header carries explicit offset/length pointers so they are not magic constants.

```
0x0000  16 bytes zero / reserved
0x0020  directory: little-endian offsets & lengths into the file, e.g.
          - a pointer 0x0000095C  = start of the sewing-data section
          - a length  0x00000294  = size of the sewing-data section (660 bytes;
                                     0x95C..0xBF0 = 0x294 — checks out)
        plus a leading word e6 00 and repeated section descriptors.
0x0050  e6 00, then an embedded ASCII path, e.g.
          ":\Users\SIGINT\AppData\Roaming\PS-300(B)\..."
        (the app's working / last-used path — privacy-relevant, see note)
0x00DC  MACHINE MODEL NAME, NUL-terminated ASCII: "KE430F\0 "
        (identical string to the machine's .PRM name; this is the output target)
0x00F0  default parameter words: 00 80 00 80 00 80 00 80  (0x8000 placeholders)
0x0100  01 00 01 00 73 00 00 00 ...  small editor settings
0x0130  .. 0x07FF   zero padding / reserved outline space
0x0800  PREVIEW BITMAP: a small dithered 1-bpp thumbnail of the pattern
          (e.g. 75 2A 52 95 29 4A 94 A5 ...), ~64 bytes, rest zero
0x0910  SEWING-DATA SECTION HEADER:
          04 00 40 00 .. 94 02 00 00 (=0x294 length) .. 02 00 (block count?)
          followed by small per-block descriptors
0x095C  EMBDATA RECORDS (needle points + codes) — see section 3
0x0BF0  EOF
```

### Embedded path / PII note

`.emb` files capture an absolute filesystem path from the machine that saved them
(here `…\Users\SIGINT\AppData\Roaming\PS-300…`). Anyone you share an `.emb` with
can read that path. Worth scrubbing before distribution.

---

## 3. Sewing-data section — `EMBDATA` records  [HYPOTHESIS / partially decoded]

The codec DLL exposes the stitch list as a C++ `CArray<EMBDATA>` produced by
`GetSewingData(header&, CArray<EMBDATA>&)`. In the file, the section at `0x095C`
is a sequence of:

The section is a list of **segments**. Each segment is:

```
0E 02 00 tt        marker:  0E02 = record magic, tt = segment type
<fields>           a few little-endian fields (counts/flags), length depends on tt
CODE (uint16 LE)   stitch/needle CODE word: 0xFFFF = normal stitch,
                                            0x6666 = segment start / tie-in
<(X,Y) ...>        run of absolute int16-LE needle points (1/400 mm) until the
                   next 0E 02 00 tt marker
```

Segment types `tt` observed:

| tt | meaning |
|----|---------|
| `0x10` | **Segment start / tie-in** (carries code `0x6666`). |
| `0x20` | **Stitch run** (carries code `0xFFFF`); the bulk of the needle points. The 4-byte id field after the marker also carries per-stitch **split-needle** attributes (e.g. `08 01 01 00` vs `08 00 00 00`). |
| `0x0F` | **OPTION code** (one trailing point = where it applies). Id field flags the option: `00 01 00 00`=opt1, `00 00 01 00`=opt2, `00 00 00 01`=opt3. |
| `0x03` | **DECELERATION code** (one trailing point). Id field byte[3] = level: `00 00 00 00`=off, `00 00 00 07`=level 7. |
| `0x01` | **Control record** (no geometric points; trailing bytes are fields, not coordinates — must be skipped, not read as XY). |

> Confirmed by `codesonly.emb` (a stitch line with all seven Code-List codes
> inserted). The family split here — option = `tt=0x0F`, deceleration = `tt=0x03`,
> split-needle = stitch-run attribute — is what disambiguated the matching `.sew`
> code opcodes (`FE`=split, `FC`=option bitmask, `FB`=decel-level, `FD 00`=trim).
> A trim/tie-off is stored in the `.emb` as a `tt=0x10` record with code `0x6666`
> at the trimmed stitch (adding a trim to `codesonly` appended exactly one such
> record); `0x6666` is the tie/lock-stitch code, used at element start and end.
> See [sew-format.md §3.3](sew-format.md) and `analysis/codes_correlate.py`.

Worked example — first bytes of `QS Plus Tack.emb` at `0x0D8C`:

```
0E 02 00 10  08 01 00 00  00 00 00 08  03 00 00 00   marker tt=0x10 + fields
66 66                                                 CODE = 0x6666 (tie-in)
D2 F6 82 F3   22 F7 82 F3                              pts (-2350,-3198)(-2270,-3198)
0E 02 00 0F  …                                         next segment
```

So the practical model is: **needle points are absolute int16 (X,Y) at 1/400 mm**;
`0E 02 00 tt` markers delimit segments; the **CODE word** (`0x6666` start/tie vs
`0xFFFF` normal) tags the stitch type, mirroring the `.sew` sew-start vs stitch
distinction. A robust extractor that walks marker-to-marker and skips `tt=0x01`
control records is in [`analysis/emb_extract.py`](analysis/emb_extract.py); on
`QS Plus Tack.emb` it reproduces the geometry to **X[-117,+118], Y[-194,+194]
steps**, matching the bounding box stored in the corresponding
`Examples/ISMS0201.sew` — the cross-check that validates the `.emb` decode.

> Still partial: the exact meaning of the per-segment field bytes between the
> marker and the CODE word (counts/flags), and the full code vocabulary beyond
> `0x6666`/`0xFFFF` (tension/speed/feed/trim values). Geometry extraction is
> reliable; per-code extraction is best-effort. The `header` struct (passed
> alongside the `CArray<EMBDATA>`) likely mirrors the 0x00–0x12F header region.

---

## 4. Reading an `.emb` (recipe)

1. Read the machine model name at `0x00DC` (NUL-terminated ASCII).
2. Read the sewing-data section pointer/length from the header directory near
   `0x0020` (LE offset to ~`0x095C`, LE length `0x0294`).
3. Walk the section segment by segment:
   - on `0E 02 00 tt` → start a segment; skip its fixed fields (≈14 bytes for
     `tt`=0x10/0x20, ≈10 for 0x0F) and read the 2-byte CODE word;
   - then read int16 LE (X,Y) needle points until the next `0E 02 00 tt`;
   - **skip `tt=0x01` control segments** — their trailing bytes are fields, not
     coordinates.
4. Convert coordinates: `mm = value / 400`, or `machine_step = value / 20`.

A robust extractor is in [`analysis/emb_extract.py`](analysis/emb_extract.py)
(and a simpler linear dump in [`analysis/emb_section.py`](analysis/emb_section.py)).

## 5. Relationship to `.sew` and to "outlines"

PS-300B's data model has three layers (see
[software-overview.md](software-overview.md)):

1. **Outline** — editable vector shapes (lines, polylines, arcs, parametric
   bartack/eyelet/etc. objects). Stored in `.emb` (the reserved space below the
   header). "Clear Stitch" removes generated stitches but keeps the outline;
   "Clear Outline" keeps stitches but drops the editable shape.
2. **Sewing data** — the generated needle points + codes (`EMBDATA`), the part
   decoded above. Also stored in `.emb`.
3. **Machine file** — `.sew`, produced by *exporting* the sewing data through the
   selected machine's `.PRM` (down-sampled 20:1 to machine steps and packed into
   the BIL container).

`.emb` therefore *supersets* `.sew`: every `.sew` can in principle be
reconstructed from its `.emb`, but not vice-versa (the `.sew` lacks the editable
outline and runs at coarser resolution).

`.emb` can also be exported to **DXF** (vector outline) for use in CAD, and
imported *from* DXF / BMP / JPG (image tracing) — those paths are handled by the
main application, not the machine import/export DLL.
