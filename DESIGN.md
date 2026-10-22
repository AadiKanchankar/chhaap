---
name: Chhaap
description: A block-printer's sample book on the workbench for local Warli design generation, from a written brief to print files.
colors:
  geru: "#9a4527"
  geru-deep: "#6f2c15"
  geru-deeper: "#5c230f"
  geru-line: "#b8644a"
  rice: "#f2e9d8"
  rice-2: "#e7dbc3"
  rice-3: "#d9c9aa"
  ink: "#231e1a"
  ink-2: "#594a3d"
  indigo: "#2b3c74"
  indigo-deep: "#1d2a55"
  on-geru: "#f6ecdb"
  error-oxide: "#8c1d0e"
typography:
  display:
    fontFamily: "Rozha One, Georgia, serif"
    fontSize: "2.5rem"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Rozha One, Georgia, serif"
    fontSize: "1.75rem"
    fontWeight: 400
    lineHeight: 1.1
  title:
    fontFamily: "Rozha One, Georgia, serif"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: 1.1
  caption:
    fontFamily: "Rozha One, Georgia, serif"
    fontSize: "1.15rem"
    fontWeight: 400
    lineHeight: 1.35
  body:
    fontFamily: "Hind, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "tnum"
  label:
    fontFamily: "Hind, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.55
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "0.8rem"
    fontWeight: 400
rounded:
  none: "0"
spacing:
  s1: "4px"
  s2: "8px"
  s3: "12px"
  s4: "16px"
  s5: "24px"
  s6: "32px"
  s7: "48px"
components:
  button-stamp:
    backgroundColor: "{colors.indigo}"
    textColor: "{colors.rice}"
    typography: "{typography.title}"
    rounded: "{rounded.none}"
    padding: "12px 24px 10px"
    height: "48px"
  button-stamp-hover:
    backgroundColor: "{colors.indigo-deep}"
  button-stamp-disabled:
    backgroundColor: "{colors.ink-2}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "8px 12px"
    height: "40px"
  button-quiet-hover:
    backgroundColor: "{colors.rice-2}"
  button-quiet-strong:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
    height: "44px"
  example-chip:
    backgroundColor: "{colors.rice-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "8px 12px"
    height: "36px"
  example-chip-hover:
    backgroundColor: "{colors.rice-3}"
  product-card:
    backgroundColor: "{colors.rice-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "8px 8px 8px 12px"
    height: "96px"
  product-card-hover:
    backgroundColor: "{colors.rice-3}"
  product-card-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.rice}"
  choice-chip:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "4px 10px"
    height: "34px"
  choice-chip-hover:
    backgroundColor: "{colors.rice-2}"
  choice-chip-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.rice}"
  palette-swatch:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.none}"
    padding: "3px"
  palette-swatch-selected:
    textColor: "{colors.ink}"
    padding: "2px"
  symbol-chip:
    backgroundColor: "{colors.rice-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "3px 6px 3px 3px"
    height: "30px"
  textarea-brief:
    backgroundColor: "{colors.rice}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "12px"
  select-underline:
    backgroundColor: "{colors.rice}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "4px 0"
    height: "38px"
  input-number:
    backgroundColor: "{colors.rice}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "4px 0"
  tab:
    backgroundColor: "{colors.geru-deep}"
    textColor: "{colors.on-geru}"
    rounded: "{rounded.none}"
    padding: "12px 16px 10px"
    height: "44px"
  tab-selected:
    backgroundColor: "{colors.rice}"
    textColor: "{colors.ink}"
  proof-sheet:
    backgroundColor: "{colors.rice}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "{spacing.s5}"
  gallery-item:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "{spacing.s2}"
  gallery-item-hover:
    backgroundColor: "{colors.rice-2}"
---

# Design System: Chhaap

## Overview

**Creative North Star: "The Sample Book on the Workbench"**

Chhaap is a block-printer's sample book laid on a geru-plastered board. Every working surface is a rice-paste sheet pinned to that red-ochre ground, marked at its four corners with registration crosses; the masthead is a darker strip of the same plaster. Ink is charcoal. One accent, block-print indigo, is reserved for the live action and the active state, so the eye always finds the press.

Colour fields are flat and unmodulated: no gradients, no glass, no paper texture faked in CSS. The only texture on screen belongs to the generated designs and their mockups. Corners are square everywhere, edges are inked rules (2px for structure, 1px for subdivision), and numbers sit in fixed tabular cells, like a job ticket. Density is that of a working tool: two columns at desktop (the brief on the left, the proof book on the right), one column on phones with the press pinned to the bottom edge.

**Key Characteristics:**
- Geru board, rice-paste sheets, charcoal ink, one indigo accent.
- Square corners; inked 2px structural rules, 1px or dashed subdivisions.
- Corner registration crosses on every sheet.
- Swatch-book tabs cut from the board colour.
- A single indigo stamp button that presses down on click.
- Carved-block choices that invert to charcoal when chosen.
- Tabular numerals throughout.

## Colors

An earth palette from Warli wall painting (red-ochre plaster, rice paste, soot), with one printer's indigo held back for action.

### Primary
- **Block-print Indigo** (`indigo`): the Print design stamp (and the study Save stamp), focus outlines, text selection, links, range and checkbox accents, the chosen study image. Its deeper shade (`indigo-deep`) is the stamp border and hover.

### Neutral
- **Geru Red-Ochre** (`geru`): the page board behind every sheet, and the tab strip.
- **Burnt Geru** (`geru-deep`): masthead and unselected tabs. `geru-deeper` is the tab hover.
- **Geru Line** (`geru-line`): the 1px rule around the machine-status chip on the masthead.
- **Rice Paste** (`rice`): sheet surface, selected tab, the brief textarea, underline selects and number fields.
- **Rice Paste Shade** (`rice-2`): carved product cards and example chips at rest, symbol chips, hover fills, the plan JSON block, the empty mockup plate and image wells.
- **Rice Paste Edge** (`rice-3`): hairline dividers between rows, unchosen swatch borders, hover on carved cards and example chips, scrollbars.
- **Charcoal Ink** (`ink`): all body text, structural rules, chosen cards and chips, symbol masks, plate grounds.
- **Faded Ink** (`ink-2`): hints, captions, field and plan-row labels, art-form subheads, the dashed lost rule, disabled stamp.
- **Paste on Geru** (`on-geru`): text sitting directly on the geru board or masthead.
- **Oxide Error** (`error-oxide`): status line when a print fails; nowhere else.

### Named Rules
**The One Stamp Rule.** Indigo marks the live action and the active state only. A screen has one indigo stamp in view; every other action is a quiet button, and everything else selected is charcoal on rice.

**The Flat Field Rule.** Every colour is a flat field. No gradients, no tints layered over tints, no CSS paper grain.

## Typography

**Display Font:** Rozha One (with Georgia, serif)
**Body Font:** Hind (with system-ui, sans-serif), weights 400 / 500 / 600
**Label/Mono Font:** JetBrains Mono, inside the Under the hood panel only

**Character:** Rozha One is a high-contrast Devanagari-and-Latin display face with the weight of a carved block; Hind is a plain, legible Indian text face that carries labels and prose without competing. The wordmark pairs Latin and Devanagari (Chhaap / छाप).

### Hierarchy
- **Display** (400, 2.5rem / 2rem on phones, line-height 1): the wordmark only.
- **Headline** (400, 1.75rem, 1.1): sheet titles ("The brief", "Study").
- **Title** (400, 1.25rem, 1.1): stage headings, Provenance headings, meaning-card section heads ("Present in this design", "Placed but lost in generation"), the stamp label, the Devanagari wordmark. Rozha also sets the study lede (1.4rem / 1.3), meaning-card entries (1.15rem) and the story-beat numerals (1.1rem).
- **Caption** (400, 1.15rem, 1.35): the Rozha caption under the mockup plate, capped at 60ch.
- **Body** (400, 1rem, 1.55): prose, the brief textarea (line-height 1.5) and number fields, capped at 60-70ch. Readout values step up to 1.05rem at 600.
- **Label** (400-600, 0.75-0.95rem): tabs, selects and beat-name fields (500, 0.95rem); quiet buttons, product names, status lines and card context (0.9rem); field labels, hints, captions, example and choice chips, art-form subheads (600) and notes (0.875rem); plan-row keys and source lines (0.8rem); readout terms, step labels, swatch names, product notes, symbol chips and gallery dates (0.75rem).
- **Mono** (400, 0.8rem): the plan JSON block, the survival table, prompt lines and timings in Under the hood.

### Named Rules
**The Tabular Ticket Rule.** `font-variant-numeric: tabular-nums` is set on the body; numbers in readouts, scores and the survival table sit in fixed cells and never shift width.

**The Mono-Under-the-Hood Rule.** JetBrains Mono appears only where the model's internals are shown. Everywhere else is Hind or Rozha One.

## Layout

A two-column workbench: the brief sheet (minmax(300px, 380px), sticky at 16px) on the left, the proof book (fluid) on the right, max width 1600px, gutters and outer padding clamp(16px, 2.2-3vw, 32-40px). Spacing runs on a 4px-based scale (4, 8, 12, 16, 24, 32, 48); sheets pad at 24px, sheet groups and panel sections stack at 24px, controls group at 8-12px.

The brief sheet reads top to bottom as a job ticket: brief textarea and example chips, product cards, the Read the brief row, the plan card, then Press settings, collapsed by default. The plan card is a stack of rows, each a 4.6rem key column beside its control, under a 2px charcoal top rule; it sits at 55% opacity until a brief has been read. The proof book holds seven tabs: Design, Under the hood, Repeat, Meaning card, Export, Gallery, Provenance. Design stacks the mockup plate, its caption, the press row (stamp and status), the step strip, the readout and the deliverable thumbnails.

Grids use auto-fill minimums: product cards 98px, palette swatches 68px, step thumbnails 72px, deliverables 150px, export files 220px, gallery items 240px. The readout is a fixed 3-column grid; Under the hood stages are two columns (1 : 1.3).

Below 900px the bench collapses to one column, the brief stops being sticky, Under the hood stages stack, and the press row becomes a fixed rice-paste bar at the bottom of the viewport (96px body padding reserves its space). Below 560px tabs wrap, plates stack, and the wordmark drops to 2rem.

## Elevation & Depth

Hybrid: flat colour fields, with one physical metaphor. Sheets are paper pinned to a board, so they cast a soft warm shadow onto the geru; nothing on a sheet is lifted except the stamp button, which presses down on click.

### Shadow Vocabulary
- **Pinned sheet** (`box-shadow: 0 10px 24px -8px rgba(48, 16, 4, .55), 0 2px 4px rgba(48, 16, 4, .25)`): every sheet resting on the board.
- **Stamp at rest** (`box-shadow: 0 3px 6px -1px rgba(29, 42, 85, .5)`): the indigo stamp button; collapses to `0 1px 2px` with a 2px drop on `:active`.
- **Press bar** (`box-shadow: 0 -6px 16px -6px rgba(48, 16, 4, .45)`): the fixed bottom press bar on phones.

### Named Rules
**The Paper-on-Board Rule.** Shadows are soft and warm-tinted from the geru, never hard offset blocks. Only sheets, the stamp, and the phone press bar carry one.

## Shapes

Square corners throughout (0 radius); nothing is rounded. Form comes from inked borders: 2px charcoal for structure (the brief textarea, product cards, the plan card's top rule, the mockup plate, the repeat frame, the top rules of readouts, stage lists, survival-table heads and meaning cards, the strong quiet button, a chosen swatch), 1px charcoal for subdivision (quiet buttons, example, choice and symbol chips, thumbnails, file cards, gallery items), 1px Rice Paste Edge for row dividers. Underline fields carry only a bottom rule: 2px on selects and number fields, 1px on beat names and the Add symbol select. Dashed borders mean empty, off or lost: the empty mockup plate, a symbol chip about to be removed, and the top rule of the lost section of the meaning card. Each sheet carries four 18px registration crosses (a circle on a crosshair, 1px charcoal SVG) inset 6px from its corners.

Product glyphs and the remove-beat cross are drawn SVG line art on a 40-unit grid, one 1.6 stroke in the current text colour, so they invert with the card.

## Components

### Buttons
- **Shape:** square (0), inked border.
- **Stamp (primary):** indigo fill, rice Rozha One label at 1.25rem, 2px Indigo Deep border, 48px tall. One per view: Print design on the workbench, Save in the study annotation task.
- **Hover / Active / Disabled:** hover deepens to Indigo Deep; active drops 2px and flattens the shadow over 120ms (ease cubic-bezier(.16, 1, .3, 1)); disabled turns Faded Ink with a progress cursor.
- **Quiet (secondary):** transparent, 1px charcoal border, Hind 500 at 0.9rem, 40px tall; hover fills Rice Paste Shade; disabled drops to 50% opacity. Read the brief, Add a beat, New seed, study Left / Right.
- **Quiet strong:** the quiet button with a 2px border, 600 weight, 44px tall and 16px side padding. The weightiest action that is not the stamp (Prepare print files), so the stamp stays single.
- **Remove (×):** a 32px transparent square holding a 20px drawn cross in Faded Ink; hover shows a 1px charcoal border and darkens the cross.

### Chips
- **Example chips:** Rice Paste Shade, 1px charcoal border, Hind 500 at 0.875rem, 36px tall; hover deepens to Rice Paste Edge. Clicking one fills the brief.
- **Choice chips (radio):** the plan's Layout, Repeat and Density choices. Separate 1px charcoal chips, 4px apart and wrapping, 0.875rem, 34px tall; hover fills Rice Paste Shade; the chosen chip inverts to charcoal with rice text.
- **Symbol chips:** a 20px masked symbol glyph beside a 0.75rem name, Rice Paste Shade with a 1px charcoal border, 30px tall. Clicking removes the symbol, so hover turns the border dashed and fades the text.

### Cards / Containers
- **Sheet:** square, Rice Paste on the geru board, Pinned sheet shadow, no border, registration crosses at the corners, 24px padding.
- **Product cards (carved blocks, radio):** Rice Paste Shade with a 2px charcoal border, at least 96px tall, left-aligned: a 40px drawn product glyph, the name (500, 0.9rem), a 0.75rem Faded Ink note. Hover deepens to Rice Paste Edge; chosen inverts to charcoal with rice text and a Rice Paste Edge note.
- **Plan card:** a borderless fieldset under a 2px charcoal top rule, rows of key and control 12px apart. Story beats are a numbered list: a Rozha numeral, an underline beat-name field and a remove cross, then the beat's symbol chips and an Add symbol select, each beat closed by a 1px Rice Paste Edge rule.

### Inputs / Fields
- **Brief textarea:** Rice Paste, 2px charcoal box, 12px padding, Hind 1rem, at least 7.5em tall, vertical resize; Faded Ink placeholder.
- **Underline selects and fields:** no box, Rice Paste ground, 2px charcoal bottom rule, Hind 500 at 0.95rem (selects 38px tall). Number fields match at 1rem. Beat names and the Add symbol select use a 1px rule; beat names darken it on hover.
- **Palette swatches (radio):** a 22px strip of the palette's four colours (ground at double width, then ink, accent, border) over a 0.75rem name; 1px Rice Paste Edge border at rest, charcoal on hover. Chosen thickens to a 2px charcoal border and sets the name in 600 charcoal; swatches never invert, because the colours are the content.
- **Ranges and checkboxes:** native, with the indigo accent colour.
- **Focus:** global 2px indigo outline, 2px offset.
- **Disclosure:** Press settings is a 600-weight summary with a drawn chevron (7px, 2px charcoal stroke) that turns from pointing right to pointing down over 200ms; hover underlines the label. Collapsed by default.

### Navigation
- **Swatch-book tabs:** a geru strip bleeding to the sheet edges; tabs are Burnt Geru with Paste on Geru text (500, 0.95rem), 44px tall, set 8px down; the selected tab turns Rice Paste, rises to the strip top and joins the sheet. Hover darkens the tab. On phones they wrap.

### Mockup Plate
The Design panel's main figure. Empty, it is a dashed 2px Faded Ink frame on Rice Paste Shade, at least 320px tall, with a centred prompt. Once a design lands the frame turns solid charcoal on a charcoal ground, sized to the mockup, and the image arrives with a 550ms stamp settle (slight scale, blur clearing to sharp). The Rozha caption sits beneath it. Deliverable thumbnails follow as 150px contained images on Rice Paste Shade with 1px charcoal borders and capitalised captions.

### Readout
A job ticket: 3-column grid under a 2px charcoal top rule, each cell a 0.75rem Faded Ink term over a 1.05rem 600 value, divided by 1px Rice Paste Edge rules.

### Under the Hood
Numbered stages under a 2px charcoal top rule and 1px dividers, prose on the left and evidence on the right. The plan JSON is a mono block on Rice Paste Shade, scrolling past 18em. The survival table is mono, with Faded Ink 500 heads over a 2px charcoal rule and 1px Rice Paste Edge row rules; rescued rows set the result in 600 charcoal, and lost rows are struck through in Faded Ink.

### Meaning Card
Entries are a 56px masked symbol beside a Rozha 1.15rem name, the meaning, Faded Ink context and a source line, separated by 1px Rice Paste Edge rules under a 2px charcoal top rule. When some symbols did not survive, the card splits under two Rozha 1.25rem heads, "Present in this design" and "Placed but lost in generation", with 600 0.875rem Faded Ink art-form subheads (Warli, Mandana) inside. The lost section opens with a 2px dashed Faded Ink rule and its entries sit at 75% opacity.

### Gallery
A grid of mockup buttons: 1px charcoal frame, 8px padding, a 4:3 cover image on Rice Paste Shade, the brief clamped to three lines at 0.9rem and a 0.75rem Faded Ink date. Hover fills Rice Paste Shade.

## Do's and Don'ts

### Do:
- **Do** set every working surface as a Rice Paste sheet on the geru board, with the four registration crosses and the Pinned sheet shadow.
- **Do** keep indigo to one stamp button per view plus focus, selection, links and native control accents; give any second weighty action the strong quiet button.
- **Do** show selection by inverting to charcoal on rice (product cards, choice chips); where the content is colour (palette swatches), thicken the border to 2px charcoal instead.
- **Do** use dashed borders only to mean empty, off or lost.
- **Do** draw icons as SVG line art in the current colour (one 1.6 stroke on a 40-unit grid).
- **Do** keep numbers in fixed tabular cells.
- **Do** honour `prefers-reduced-motion`: all animation and transitions switch off.

### Don't:
- **Don't** round a corner.
- **Don't** use gradients, glass, CSS paper texture or emoji.
- **Don't** use hard offset shadows; depth is the soft warm Pinned sheet shadow only.
- **Don't** put a second indigo stamp in view.
- **Don't** use JetBrains Mono outside Under the hood.
- **Don't** build a sidebar-plus-KPI-card dashboard; the bench is a brief and a proof book.
