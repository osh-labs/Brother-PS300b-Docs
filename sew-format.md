# The `.sew` machine file format (Brother ISM)

> Status: container **[CONFIRMED]**, in-block stitch encoding **[CONFIRMED]**,
> feed/control records **[STRONG/HYPOTHESIS]**.

The `.sew` file is the **machine-ready** form of a pattern. PS-300B *exports* a
pattern to one or more `.sew` files which are then copied to machine media
(floppy via the FD300 unit, serial/COM, or burned to a ROM chip) and loaded by a
Brother **ISM** (Individual Stitch Memory) sewing head — e.g. the KE430 bartack
machine.

The same physical pattern, when held in the editor, lives in a [`.emb`](emb-format.md)
file. `.sew` is the lower-level, machine-coordinate representation.

Naming: exported files are named `ISMS0NNN.sew` (e.g. `ISMS0200.sew`) and written
into a machine-specific folder such as `BROTHER\ISM\ISMDA00\` (the folder and the
`NNN` numbering come from the machine's `.PRM` path template — see
[machine-prm-rom-formats.md](machine-prm-rom-formats.md)).

---

## 1. Units

| Quantity | Unit | Notes |
|----------|------|-------|
| `.sew` coordinate / delta | **0.05 mm** (1/20 mm) | = one machine step. Matches the `0.05` scale factor stored in the KE430 `.PRM`. |
| KE430 field | ±400 × ±300 steps | = 40 mm × 30 mm. Patterns exceeding this are rejected ("This data exceeds frame area"). |

So a magnitude byte of `0x50` (= 80) is **80 × 0.05 mm = 4.0 mm** of needle travel.

**Coordinate frames:** stitch/feed *deltas* are in **editor coordinates** (X
right, Y up). The bounding box stored in `chunk 0x0003` is in **machine
coordinates**, which **negate Y** (X unchanged). Account for this when comparing
a decoded path to the stored bbox, and when writing a file.

---

## 2. Container structure  [CONFIRMED]

```
+0x00  "BIL\0"                      4 bytes  magic
+0x04  23 13 00 c8                  4 bytes  format/version tag (constant in all samples)
+0x08  00 00                        2 bytes
+0x0A  <uint16 LE>                  2 bytes  checksum/uid (varies per file; see note)
+0x0C  00 00 00 00                  4 bytes  reserved
+0x10  <chunks...>
```

The 16-byte header is followed by a sequence of **chunks**. Every chunk:

```
CD 0C 00 00          chunk sentinel / magic (4 bytes)
LL LL                payload length, uint16 BIG-ENDIAN
TT TT                chunk type,     uint16 BIG-ENDIAN
00 00 00 00          reserved (4 bytes)
<payload>            LL bytes
```

(Length and type are **big-endian**; everything else in the file is little-endian.
This is the one gotcha in the format.)

### Chunk types observed

| Type | Meaning | Payload |
|------|---------|---------|
| `0x0002` | **Resolution / scale descriptor** | 4× uint16 BE = `500 1000 500 1000` in *every* sample. Treat as a fixed constant (X res, Y res, …). |
| `0x0003` | **Pattern info / bounding box** | 9× int16 BE. See below. |
| `0x0004` | **Stitch data** | The packed stitch byte-stream (section 3). |
| `0x0005` | **Label** | 64-byte NUL-padded ASCII, always `"PS-300B ISM Data"`. |
| `0x000D` | **Timestamp** | 6× int16 BE = `year, month, day, hour, minute, second`. e.g. `2026, 6, 9, 18, 35, 3`. |
| `0x0001` | **End of file** | length 0, no payload. |

### Chunk `0x0003` (pattern info), 9 × int16 BE

```
word[0]  uid/checksum     (varies wildly between files; not geometric)
word[1]  ? (small signed) 
word[2]  ? (small signed)
word[3]  111   (constant in all samples — likely a machine/format constant)
word[4]  -1    (constant)
word[5]  maxX   ┐
word[6]  minX   │  bounding box of the pattern, in machine steps (0.05 mm),
word[7]  maxY   │  MACHINE coordinates (Y negated vs the editor-coord deltas)
word[8]  minY   ┘
```

(words 1–2 also appear to be a reference point in machine coords — e.g. `(0,-100)`
for the feed-only file whose last point is editor `(-5,5)`; not fully pinned.)

For `Examples/ISMS0200.sew` (the bartack): `maxX=393 minX=-392 maxY=40 minY=-40`
→ span **785 × 80** steps = **39.25 mm × 4.0 mm**. The decoded stitch stream
reproduces exactly this span — the cross-check that validates the codec.

---

## 3. Stitch data (chunk `0x0004`)  [CONFIRMED for stitch moves]

The payload is a stream of **2-byte records**, organised into one or more
**blocks**. Decoding is sequential; the machine maintains a current (X,Y) pen
position and applies each record as a relative move.

```
record = <cmd byte> <arg byte>
```

### 3.1 Record classification by the command byte

The command byte is a bitfield. **Classify in this order** (the data-code
opcodes `0xFB–0xFF` have bit `0x40` set, so the high-nibble test must come
first):

```
(cmd & 0xF0) == 0xF0  ->  CONTROL / DATA CODE   (0xF_ : EOF, trim, sew-start,
                                                 split, option, deceleration,
                                                 …; no needle move)
cmd & 0x40            ->  STITCH MOVE           (needle down; a stitch is formed)
else (0x00–0x3F)      ->  FEED                  (needle-up reposition)
```

### 3.2 STITCH MOVE records  [CONFIRMED]

For a stitch-move record (`cmd & 0x40` set), the command byte decomposes as:

```
bit 0x40  = 1   marks "stitch move"
bit 0x20  = SPLIT-NEEDLE flag:  1 = "Split Needle Up",  0 = "Split Needle Low"
bit 0x08  = AXIS:  1 = Y axis,  0 = X axis
bit 0x04  = SIGN:  1 = negative, 0 = positive
bits 0x10,0x02,0x01 = 0 in all observed stitch records
arg byte  = MAGNITUDE (unsigned), in machine steps (0.05 mm)
```

So **each stitch record moves exactly one axis**. A diagonal satin stitch is
encoded as a *pair* of records — one Y move and one X move — that the machine
executes as a single needle penetration cycle. The "Split Needle Up/Low" bit
(0x20) alternates across the satin column and corresponds to the editor's
**"Split Needle Up" / "Split Needle Low"** stitch types (the two sides of a
zig-zag / split stitch).

#### The six common stitch command bytes

| cmd | bin | needle | axis | sign | meaning |
|-----|-----|--------|------|------|---------|
| `0x60` | `0110 0000` | Up   | X | + | +X by arg |
| `0x64` | `0110 0100` | Up   | X | − | −X by arg |
| `0x68` | `0110 1000` | Up   | Y | + | +Y by arg |
| `0x6C` | `0110 1100` | Up   | Y | − | −Y by arg |
| `0x48` | `0100 1000` | Low  | Y | + | +Y by arg |
| `0x4C` | `0100 1100` | Low  | Y | − | −Y by arg |
| `0x40` | `0100 0000` | Low  | X | + | +X by arg |
| `0x44` | `0100 0100` | Low  | X | − | −X by arg |

Worked example — the bartack satin column (bytes `68 50 64 0F 4C 50 64 10 …`):

```
68 50  ->  +Y 80   (Split-Up)   = +4.00 mm  (zig across the bar)
64 0F  ->  -X 15   (Split-Up)   = -0.75 mm  (advance along the bar)
4C 50  ->  -Y 80   (Split-Low)  = -4.00 mm  (zag back)
64 10  ->  -X 16   (Split-Up)   = -0.80 mm  (advance)
...
```

That alternation (+Y / advance / −Y / advance …) drawn out for the whole column
is the satin bar; integrating it gives the 785 × 80 box stored in chunk 0x0003.

### 3.3 CONTROL / FEED / terminator records  [STRONG / HYPOTHESIS]

When `cmd & 0x40 == 0` the record is **not** a needle penetration. The
opcodes in the `0xF_` range are single-byte control codes (`cmd arg`, `arg`
often 0); the `0x00–0x3F` range carries **feed** (needle-up) moves.

#### 0xF_ opcodes — structural markers  [CONFIRMED]

| cmd | name | meaning |
|-----|------|---------|
| `0xFF` (`FF 00`) | **EOF** | End of stitch data (end of last block). |
| `0xF4` (`F4 00`) | **SEW-START** | "Begin sewing" marker emitted after the approach feed, before the first stitch of a segment. |
| `0xFD` (`FD 00`) | **THREAD TRIM** | Cuts the thread; it also naturally terminates a sewing segment (you trim at the end of each element), which is why it appears between blocks. Confirmed by a controlled edit: adding a thread-trim to the last stitch of `codesonly` made `FD 00` appear on that stitch. |

#### 0xF_ opcodes — data codes (editor "Code List")  [CONFIRMED via controlled export]

Pinned down by `Examples/ISMS0203.sew` + `codesonly.emb`, a line of dummy
stitches with these seven codes inserted left-to-right (user-stated):
*split-low, split-high, option 1, option 2, option 3, deceleration-off,
deceleration-level-7*. The `.emb` separates them by record type
(split = per-stitch attribute; option = `tt=0x0F` ×3; deceleration = `tt=0x03`
×2 carrying the level in the arg), which maps to the `.sew` opcodes as:

| cmd | code | notes |
|-----|------|-------|
| `0xFE 00` / `0xFE 01` | **Split needle High / Low** | `FE` = split-needle code; arg selects bar position (`01` = low, `00` = high). (This is the standalone code; the per-stitch `0x20` bit carries the same Up/Low choice within satin.) |
| `0xFC nn` | **Option** | `nn` is a **bitmask**: bit0 = Option 1 (`FC 01`), bit1 = Option 2 (`FC 02`), bit2 = Option 3 (`FC 04`). |
| `0xFB nn` | **Deceleration level** | `nn` = level `1–7` (`FB 07` = level 7; the QS Plus Tack's `FB 05` = level 5). **Deceleration *off* is the default and emits no code** — the editor's "deceleration off" produces an `.emb` record but no `.sew` byte. |

> Confirmed by `ISMS0203.sew`: it has 7 code bytes
> (`FE 01, FE 00, FC 01, FC 02, FC 04, FB 07, FD 00`) for the editor's
> split-low / split-high / opt1 / opt2 / opt3 / decel-L7 / **trim** — the editor's
> "deceleration off" is the one Code-List entry with no `.sew` byte. The
> `.emb`↔`.sew` X-correlation is in `analysis/codes_correlate.py`.

> Worked multi-block reference — `Examples/ISMS0201.sew` (*QS Plus Tack*): its
> `0xF_` codes decode as `F4`(sew-start), `FB 05`(decel level 5), `FD 00`(trim),
> `F4`, `FD 00`(trim), `FD 00`(trim), `FF`(eof) — i.e. for each element:
> **sew → decelerate → trim → feed to next**. The three `FD 00`s are the three
> trims the pattern needs (one per element).

#### FEED (needle-up jump) records  [CONFIRMED]

Feed moves use command bytes with `0x40` **clear**, and they reuse the **exact
same bitfield and magnitude unit as stitch moves**:

```
0x40 = 0   marks "feed" (needle up; reposition without forming a stitch)
0x08 = AXIS:  1 = Y axis,  0 = X axis
0x04 = SIGN:  1 = negative, 0 = positive   (in EDITOR coordinates, +Y up)
arg  = MAGNITUDE in machine steps (0.05 mm) — SAME 1-step unit as stitches
```

Confirmed by a controlled export, `Examples/ISMS0202.sew`: a feed-only pattern
defined in the editor as start `(0,0)` → feed `(5,5)` → feed `(-5,5)` (mm). Its
entire stitch chunk is:

```
FD 00            thread trim (here at the start, before any feed)
20 64   ->  X +100 steps  = +5.00 mm    -> (5,0)
08 64   ->  Y +100 steps  = +5.00 mm    -> (5,5)     first feed point  ✓
24 C8   ->  X -200 steps  = -10.0 mm    -> (-5,5)    second feed point ✓
FF 00            EOF
```

i.e. `0x64 = 100 = 5.00 mm` and `0xC8 = 200 = 10.0 mm` — a plain 1-step unit, and
the sign bit behaves normally (`24` = negative X). This **supersedes an earlier
guess of a coarse ×4 feed unit, which was wrong.**

**Editor vs machine Y (important for writers):** the deltas above are in *editor*
coordinates (Y up). The `chunk 0x0003` bounding box for the same file is
`maxY=0, minY=-100` — i.e. **the stored bbox is in machine coordinates, which
negate Y** (the two feed points at editor +5 mm appear at machine Y −100). X is
not flipped. So: decode/emit deltas in editor coords with normal signs; expect
the chunk-0x0003 Y extents to be the negation.

Examples of feed groups between blocks in other files: `20 04` (small approach,
before `F4 00`), `2E 01 0C 52 20 04`, `20 75 08 B6`, `24 E8 0A 03 08 14`,
`20 3A 0E 01 0C 30`, `26 01 04 04 0C 53`.

**The `0x20` bit on feed records = "start of a new jump".** A feed *move* from
the current point is emitted as up to two records — **X record first, then Y**
(note: stitches are the opposite, Y then X) — and the **first** record of the
move sets `0x20`; the continuation record clears it. In the feed-only file:
`20 64` (X +5, start-of-jump) · `08 64` (Y +5, continuation) = jump 1;
`24 C8` (X −10, start-of-jump) = jump 2. This was confirmed by reproducing the
file with the writer (`analysis/sew_write.py`) — byte-for-byte.

**Minor residual:** in the *QS Plus Tack*, feed command bytes also show `0x10`
and `0x02` bits (e.g. `0x2E`) and a couple of large inter-block Y jumps still
under-resolve, suggesting an additional feed sub-mode or magnitude extension used
for long jumps. This affects only absolute reassembly of complex multi-block
patterns, not the encoding of an individual feed.

#### Other editor codes (not yet individually isolated)

Mapped so far: split-needle (`FE`), option (`FC`), deceleration level (`FB`),
**thread trim (`FD 00`)**, sew-start (`F4 00`), EOF (`FF 00`); deceleration-off =
default/no code. From the editor "Code List", **still to map**:
**Thread Tension / Two-Step / Digital Tension** (≤99 per pattern), **Change
Speed (Speed 0–7)**, **Cutter On**, **Stop Needle Upper/Lower Position**,
**Second / Machine Original Point**.

> To finish the code map: export single-code test patterns (one trim only; one
> speed change; one tension code; a Speed-0..7 sweep) the same way as
> `codesonly.emb`/`ISMS0203.sew`, and diff the `0x0004` payloads —
> `analysis/codes_correlate.py` already aligns `.emb` codes to `.sew` bytes by
> position. The alternative is disassembling `PS300BMachineImportExportENU.dll`.

---

## 4. Reading a `.sew` (recipe)

1. Check magic `BIL\0`.
2. Walk chunks from offset `0x10` using the `CD 0C 00 00` / BE-length / BE-type
   layout until type `0x0001`.
3. From chunk `0x0003`, read the bounding box (words 5–8) for a sanity target.
4. Decode chunk `0x0004`:
   - position `(x,y) = (0,0)`.
   - for each `cmd,arg`:
     - test `(cmd & 0xF0)==0xF0` FIRST (codes have 0x40 set):
       `0xFF`→stop; `0xFD`→**Trim**; `0xF4`→**sew-start**; `0xFE`→split;
       `0xFC`→option (bitmask); `0xFB`→deceleration level. None move the needle.
     - `cmd & 0x40` → stitch: `d = (cmd&0x04 ? -arg : +arg)`; if `cmd&0x08`
       apply to Y else X; record a needle point at the new `(x,y)`; the
       `cmd&0x20` bit is the split-needle sub-type (Up/Low).
     - else (`0x00–0x3F`) → **feed** (needle up): same axis/sign bits and same
       1-step magnitude unit as a stitch; apply to position without recording a
       stitch. (Ignore the extra `0x20/0x10/0x02` flag bits for position.)
5. Multiply step counts by **0.05 mm** for real-world coordinates (deltas are in
   editor coords; negate Y to compare against the chunk-0x0003 machine bbox).

A reference decoder is in [`analysis/sew_decode_verify.py`](analysis/sew_decode_verify.py).

## 5. Writing a `.sew` (recipe)

A working writer is implemented in [`analysis/sew_write.py`](analysis/sew_write.py).
Given the editor program `start(0,0) → feed(5,5) → feed(-5,5)` it produces a file
**byte-for-byte identical to the genuine PS-300B export `ISMS0202.sew`, except
the single checksum word** (chunk 0x0003 word0). So the format is, in practice,
fully writable. Steps:

1. Emit header `42 49 4C 00 23 13 00 C8 00 00 00 00 00 00 00 00` (the uid word at
   +0x0A can be 0; the original computes a value but the loader has not been seen
   to reject 0 — **verify on hardware/emulator before production use**).
2. Chunk `0x0002` = `01F4 03E8 01F4 03E8` (the constant `500 1000 500 1000`, BE).
3. Chunk `0x0003` = checksum-word + `[0, minY]` + `[111, -1]` + bounding box
   (BE int16, machine coords). The leading checksum word is the **one value not
   yet reproducible** (see caveats); all other fields are derived from the path.
4. Chunk `0x0004` = your stitch stream:
   - decompose every diagonal **stitch** move into a Y record then an X record;
   - choose the split-needle bit per satin side (alternate Up/Low as the
     originals do, or hold one value for plain running stitch);
   - emit **feeds** (needle-up jumps) as `0x00–0x3F` records (axis 0x08, sign
     0x04, 1-step magnitude), e.g. `20 64` = feed +X 5 mm; mark **sew-start**
     after an approach feed with `F4 00`; insert data codes as needed
     (`FE`=split, `FC`=option, `FB`=decel level); a **thread trim** is `FD 00`;
   - keep every per-record magnitude within the machine's **max pitch** and the
     whole path within the **frame area** (the exporter enforces both);
   - end each sewing element with a trim `FD 00`; finish the file with `FF 00`.
5. Chunk `0x0005` = `"PS-300B ISM Data"` padded to 64 bytes.
6. Chunk `0x000D` = timestamp.
7. Chunk `0x0001` = end.

> **The two checksum words** — header `+0x0A` and chunk-0x0003 word0 — are the
> only un-reproduced fields. They vary per file and behave like CRC-16 values;
> they are **not** any of the common CRC-16 variants (CCITT/XMODEM/MODBUS/ARC/…)
> over the obvious ranges (stitch payload, header, whole file). Whether the
> machine validates them is unknown without hardware. Until that's settled: copy
> them from an equivalent genuine export, or set 0 and test. Other caveats:
> (b) the extra feed flag bits (`0x10/0x02`) seen in complex multi-block exports
> may select a feed sub-mode — match the originals if you reproduce those;
> (c) include whatever start/end codes the machine firmware expects. The stitch
> geometry, feeds, trims, and sew-start are decoded well enough to author
> single-block and feed-only patterns directly; for the first hardware trials,
> still **diff your output against an original PS-300B
> export** of an equivalent pattern, and test on the machine before production.
