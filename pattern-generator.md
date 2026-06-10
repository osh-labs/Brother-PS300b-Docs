# The PS-300B Pattern Generator

> Status: interface + pattern catalogue + dialog/parameter structure
> **[CONFIRMED]** (read from `PatternGenerater*.dll` resources & exports). Exact
> numeric ranges/defaults of each field **[not extracted]** (they live in the
> dialog templates / code, not as plain strings).

The **Pattern Generator** is PS-300B's *parametric* design engine: instead of
drawing an outline by hand, you pick a pattern *type* (bartack, eyelet, …) and
fill in numeric parameters, and the generator computes the needle points and
codes for you. It is the tool that produced `Examples/bartack.emb`.

It ships as a separate per-language DLL — `PatternGeneraterENU.dll` (ENU/CHS/FRA/
JPN) — loaded by `PS300B.exe`.

---

## 1. Interface & data flow  [CONFIRMED]

The DLL exposes one C++ class, `CPPatternGeneraterInterface<LANG>`, with two
public methods (from the export table):

```cpp
int  StartPatternGenerater(CString name, double n, int& out);   // run the Pattern Wizard
void GetSewingData(header& hdr, CArray<EMBDATA>& data);          // retrieve the result
```

- **`StartPatternGenerater`** opens the **Pattern Wizard** (a property-sheet
  dialog): the user selects a pattern type and edits its parameters across
  tabbed pages, then confirms.
- **`GetSewingData`** returns the generated pattern as a `header` plus a
  `CArray<EMBDATA>` — **the exact same `EMBDATA` record array that the `.emb`
  sewing-data section stores** (absolute int16 X/Y needle points + code words;
  see [emb-format.md §3](emb-format.md)). PS-300B then drops this into the
  document and, on export, down-samples it 20:1 into a machine `.sew`
  (see [sew-format.md](sew-format.md)).

So the generator's output **is** sewing data — the same model used everywhere
else in the app. A "pattern" is just a parametric recipe for an `EMBDATA` array.

Working files seen referenced by the DLL: `\PatternParameters.vs` (parameter
preset/scratch store) and per-variant temp files `B800EDT.tmp`, `B800EFX.tmp`.

---

## 2. Pattern catalogue (the "Pattern Select" wizard)  [CONFIRMED]

The wizard's **Pattern Select** list offers:

| Group | Types |
|-------|-------|
| Bar tacks | `BARTACK`, **`_BARTACK(800Series)`**, `HALFMOON` |
| Eyelets / buttonholes | `EYELET`, and the end-shape combinations `_RECTANG`, `_ROUND`, `_RADIAL`, and pairs `_EYE_RCT/RND/RAD/TCK/TPR`, `_RCT_RND`, `_RND_RCT`, `_RAD_RND`, `_RCT_TCK`, `_RND_TCK`, `_RAD_TCK`, `_RCT_RAD`, `_RND_RAD`, `_RAD_RCT`, `_RCT_TPR`, `_RND_TPR`, `_RAD_TPR` |

The `_XXX_YYY` names are **two-end shape combinations** for buttonhole/eyelet
patterns (RCT = rectangular, RND = round, RAD = radial, TCK = tack/bar, TPR =
taper) — e.g. `_RCT_RND` = rectangular end + round end. Plain `_RECTANG` /
`_ROUND` / `_RADIAL` are single-shape variants. `HALFMOON` is a curved bartack.

The names prefixed with `_` are a distinct internal family (the 800-series
bartack and the shape-combination buttonholes); the unprefixed `BARTACK`,
`EYELET`, `HALFMOON` are the standard generators.

### Property-sheet tabs (shared building blocks)

Patterns are configured through tabs drawn from a common pool:
`BARTACK`, `BACKTACK`, `ZIGZAG`, `UNDERLAY`, `EXTRA`, `TENSION`, `EYELET`,
`HALFMOON`. Each pattern type uses the subset it needs.

### Units, resolution, and stitch types  [CONFIRMED]

- Length fields are **mm**, shown with a range `(%3.1f - %3.1f)mm` etc. Count
  fields are **stitches**, `(%d - %d)stitch`.
- Each numeric field has a selectable **adjustment step**: `1`, `2`, `0.1`,
  `0.05`, `0.025`, `0.01` (mm) — the spinner increment.
- **Stitch type** (param 11) = **Whip** or **Purl** (the two satin lay styles).
- **Rotation** options: `0 / 90 / 180 / 270 Degree`.
- Tie-offs: **Start securing stitches** / **End securing stitches** / **End
  securing shape** ("Spec meth").

---

## 3. `_BARTACK(800Series)` — focus  [CONFIRMED structure]

### 3.1 What it is

A bar-tack generator dedicated to the **Brother "800 series"** programmable
tackers — **`B800E` / `HE800A`** (and the `B800EDT` / `B800EFX` variants whose
temp files the DLL writes). These are a different machine class from the KE430
(larger head, 256 KB master ROM), and they get their **own, more capable bartack
generator** — a three-tab property sheet that produces a *structural* tack
(satin bar + running frame + back-tacks + tension control), well beyond the
single-tab standard `BARTACK`. Internally it is the `CPPatternB800E` pattern
driving three dedicated property pages: `CPPageBarTack800BarTack`,
`CPPageBackTack800BarTack`, `CPPageExtra800BarTack`.

### 3.2 The three tabs and their parameters

The property sheet is captioned `_BARTACK(800Series)` and has exactly three tabs.
Parameter numbers are the engine's parameter indices (same numbering as the
standard generator, but only this subset is used):

Default values below are read from the Pattern Wizard screenshots.

**Tab 1 — BARTACK** (the tack geometry + the running outline that frames it)

| # | parameter | unit | default |
|---|-----------|------|---------|
| 13 | Straight bartack length | mm | 40.0 |
| 14 | Straight bartack pitch | mm | 0.8 |
| 15 | Straight bartack width | mm | 4.0 |
| 17 | Running length | mm | 30.0 |
| 18 | Running pitch | mm | 2.0 |
| 19 | Running width | mm | 1.0 |

The tab's diagram shows the satin **bar** (height 13, width 15, pitch 14) sitting
inside a **running-stitch frame** (length 17, width 19, pitch 18) — i.e. a boxed,
reinforced tack rather than a bare zigzag.

**Tab 2 — BACKTACK** (lock / back-tacks at the ends)

| # | parameter | unit | default |
|---|-----------|------|---------|
| 40 | Start backtack | stitch | (count) |
| 41 | Start backtack width | mm | 0.5 |
| 42 | Start backtack pitch | mm | 0.30 |
| 43 | End backtack | stitch | 4 |
| 68 | Rear tack width | mm | 0.5 (with an enable checkbox) |

(40 and 43 are **stitch counts**, not on/off flags; 68 has a checkbox to
enable/disable the rear-tack width override.)

**Tab 3 — EXTRA** (underlay start, slow start, tension timing)

| # | parameter | unit | default |
|---|-----------|------|---------|
| 51 | Underlay sewing start length | mm | 2.0 |
| 52 | Underlay sewing start pitch | mm | 1.0 |
| 59 | Slow start stitches | stitch | 1 |
| 67 | S-End tension apply timing | stitch | 0 |

That's the **complete** 800-series bartack model: ~15 parameters. It produces a
straight satin **bar** (13–15) inside a **running-stitch frame** (17–19), with
**back-tacks** at the ends (40–43, 68), plus **underlay start**, **slow start**,
and **end-tack tension timing** (51–52, 59, 67).

### 3.3 How it compares to the standard `BARTACK`

**Correction (from the screenshots):** the 800-series tack is the *more* capable
generator, not the simpler one. The standard `BARTACK` (§4) is a **single-tab**
dialog with ~8 fields and produces a bare zigzag satin bar. `_BARTACK(800Series)`
adds, across its three tabs, **start/end back-tacks** (40–43), a **rear-tack
width** (68), an **underlay running frame** (17–19, 51–52), **slow start** (59),
and **end-tack tension timing** (67) — i.e. the structural reinforcement and
sewing-quality controls that make an objectively sturdier tack. The user
confirms the 800-series tacks are structurally better.

### 3.4 Output

Like every generator, `_BARTACK(800Series)` emits an `EMBDATA` array via
`GetSewingData`. When an 800-series model is the selected machine, the export
target/field come from that machine's `.PRM` (`B800E.PRM` / `HE800A(B800E).PRM`)
and its own output path — not the KE430's `ISMDA00\ISMS0***.SEW`.

> **Using the better 800-series tacks on a KE430 (worth testing).** The generator
> output is plain ISM `.sew` stitch data — the same format the KE430 loads from
> USB. So a tack designed with `_BARTACK(800Series)` could very plausibly run on
> the KE430HS, *provided*: (a) it **fits the 40 × 30 mm field** (the default 40 mm
> bartack length is right at the X limit — shrink it for margin), and (b) any
> codes it inserts are ones the KE430 tolerates (you noted your machine ignores
> tension/speed/cutter). Practical route: select an 800-series machine to design
> the tack, export, then copy that `.sew` to the KE430's USB and test on scrap.
> Alternatively, hand-build the same geometry directly with
> `analysis/sew_write.py` (a satin bar framed by a running outline + back-tacks +
> `FD 00` trim) targeting the KE430 field. The standard `BARTACK` (§4) is the
> only generator that natively exports through the KE430 profile, but it makes the
> plainer tack.

---

## 4. Standard `BARTACK` — minimal  [CONFIRMED from screenshot]

The standard `BARTACK` is a **single tab, ~8 fields**, and makes a plain zigzag
satin bar (no back-tacks, no underlay frame, no tension timing). Fields use
diagram letter-refs (a–e) rather than the engine parameter numbers:

| field | unit | default | notes |
|-------|------|---------|-------|
| Tack length (a) | mm | 8.0 | |
| Tack width (b) | mm | 2.0 | |
| Running length (c) | mm | 6.0 | |
| Running pitch (d) | mm | 1.0 | |
| Zigzag pitch (e) | mm | 0.9 | greyed when "Spec meth = #Stitches" (derived) |
| No. of stitches | stitch | 41 | |
| **Spec meth** | radio | #Stitches | specify the bar by **PITCH** *or* by **#Stitches** (the other is computed) |
| **End securing shape** | radio | 1 | tie-off shape option 1 / 2 / 3 |
| **Rotation** | radio | 0° | 0 / 90 / 180 / 270° |

That's it — far less than the 800-series tack. (The default 41-stitch, 8 mm × 2 mm
bar is the generator's starting point; `Examples/bartack.emb` is a resized
instance of this generator.)

### The rest of the numbered parameters belong to other patterns

The large numbered parameter pool seen in the DLL (zigzag/cutter/knife 02–10,
front/rear tack 21–39, underlay 44–58, 2-cycle 55–57, tension timing 63–67, and
the rear-tack **vector-shape** pages `Rad`/`Rct`/`Tpr`) is **not** used by the
simple standard `BARTACK`. It belongs to the **`EYELET` / buttonhole**
generators and their end-shape combinations (`_RCT_RND`, `_RAD_TPR`, …) and to
`HALFMOON` — patterns that genuinely have cutters, underlays, front/rear securing
tacks with selectable shapes, and per-stage tension timing. (An earlier draft of
this doc mis-assigned that pool to the standard bartack; corrected here.)

`EYELET` itself (single tab seen in the resources) uses: Outside dia. (a), Inside
dia. (b), Punched hole dia., Start feed (on/off), No. of stitches, Start/End
securing stitches, Rotation.

---

## 5. Practical notes

- **The generator is the easiest way to author valid sewing data** — it enforces
  machine-legal geometry and emits the same `EMBDATA` the rest of the app uses.
  Our standalone `.sew` writer (`analysis/sew_write.py`) reproduces the *output*
  format; the generator is the *input* (parametric) side.
- To **replicate a generator pattern programmatically**, the model is: tack
  geometry → satin column of needle points (the `60 28`-style records we
  decoded), framed by running stitches, with back-tacks and tie-off/trim codes
  (`FD 00`) — exactly the structures in [sew-format.md](sew-format.md).
- **Not yet extracted**: the numeric min/max/default for each field. These are in
  the dialog resource templates (and validation code), not plain strings; pulling
  them needs a resource decompiler (e.g. Resource Hacker on the DLL) or a debugger
  — a good next step if you want a full parameter spec with limits.
