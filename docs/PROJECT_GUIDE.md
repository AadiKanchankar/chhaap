# Chhaap: a guide to the whole project

Chhaap (Hindi and Marathi for "print" or "stamp") is a design tool that runs on a laptop. You write a short brief, for example "A3 frame for my parents' anniversary, wedding and harvest, maroon, busy, traditional border", and it produces a finished Warli-inspired product design: a wall frame, a saree set, a diary cover, wallpaper, phone wallpapers or a tee. Each design comes on a product mockup, with 300 DPI print files and a meaning card that explains every symbol in it, with a source for each meaning.

This guide explains what happens at each step, why it was built that way, what was measured, and what does not work yet.

## 1. The problem

Three problems motivated the project.

1. **Repeats.** Printed textiles and wallpaper need a tile whose right edge continues into its left edge and whose top continues into its bottom. A general image model asked for "a Warli pattern" draws a framed picture; repeating it shows a grid of frames.
2. **Meaning.** Warli symbols carry meanings (the marriage square, Kansari the goddess of grain, the tarpa dance). If a model draws first and a captioner guesses afterwards, the explanation printed on a product can be wrong.
3. **Design quality.** Published Warli products are not random scatters. They use structure (bands of figures, a dance ring, a central square with scenes around it), a designed palette, and a layout that fits the product.

The central idea: **place the symbols first, then let the model paint**. Because the program places every symbol itself, it always knows what is in the picture, so the meaning card can be built from data rather than guessed.

## 2. The pipeline, step by step

```
brief + product
  -> planner          (brief -> structured plan, symbols from the lexicon only)
  -> layout engine    (places hero, scenes, fillers and border at product size)
  -> stylize          (Stable Diffusion paints the line work; optional)
  -> survival check   (is every placed symbol still there? repair if not)
  -> recolour         (exact palette colour per layer)
  -> texture          (mud-wall grain on raster files)
  -> products         (print files, SVG, mockup, meaning card)
```

### 2.1 The lexicon (data/lexicon.csv)

A table of 25 Warli symbols. Each row has an id, a name, a local name, a meaning, a context, a source URL, and a `visual_rule`: a tiny drawing program. For example, the human figure is "two triangles meeting at the tip, a disc for the head, lines for arms and legs", written as `disc ...; poly ...; poly ...; line ...`. Composite symbols reuse others: the tarpa dance is a tarpa player inside a ring of 14 human figures (`circle_of human 14 ...`).

Why this matters: the lexicon is the single definition of each symbol. The same recipe draws the symbol in the layout, in the SVG, and in the survival check. Every meaning has a real source page, and every row is marked `verified_by_artisan = no`, because no Warli artist has checked it yet.

A second pack, Mandana (data/lexicon_mandana.csv, 14 motifs), was added later. Mandana is a floor and wall art of Rajasthan and Madhya Pradesh. Its sources (NIOS, Rooftop, Chantal Jumel's field notes) say it is painted by women and is most closely tied to the Meena community.

### 2.2 The planner (chhaap/planner.py)

Turns the brief into a plan: product, template, density, palette, border, a hero symbol and up to four story beats (for harvest: sowing, then reaping, then a dance at night). The plan is validated with pydantic: a plan that names a symbol not in the lexicon is rejected.

The default planner is keyword rules (no AI model). A local language model through Ollama can replace it if installed, and Claude can be used behind an explicit flag. The language model only fills in the plan; it never draws and never writes meanings. The plan is shown in the app as an editable card.

### 2.3 The layout engine (chhaap/layout.py)

This is the main component. It places elements at the real product size (pixels at 300 DPI) and records each one with its symbol, position, size, rotation, role (hero, support, filler, border) and colour layer.

Four templates:

| Template | What it does |
|:--|:--|
| Tarpa spiral | The tarpa player in the centre, dancers holding hands in 2 to 4 rings, each rotated to face outward |
| Registers | 2 to 4 horizontal bands, one story beat per band, the hero's band taller |
| Medallion | A square frame (the chauk) holding the hero, scenes in the four corners |
| All-over buti | Small motifs on a half-drop grid, for saree bodies and wallpaper |

A fifth template, Mandana rings, arranges motifs in concentric rings symmetric about 8 axes.

Rules the engine follows:
- **Scale hierarchy:** hero = 3 x support = 8 x filler.
- **No overlaps:** checked with oriented bounding boxes and a separating-axis test (rotated dancers needed this).
- **Filler pass:** dots, grass ticks, small birds and stars fill empty space until ink coverage reaches a target (0.07, 0.12 or 0.17 for sparse, balanced, dense).
- **Border kit:** strips of triangles, chevrons, dots, a leaf vine, a chain of dancers, or the two Mandana bands.
- **Repeats:** straight, half-drop or brick. Every element is also drawn at its lattice copies, so a tile wraps exactly.
- **Hand-drawn feel:** every stroke gets a small seeded jitter in width and end points.

### 2.4 Stylize: diffusion (chhaap/generate.py, chhaap/studio.py)

The black-and-white layout drawing goes through:
- **Stable Diffusion 1.5**, the open image model;
- **ControlNet (scribble)**, which forces the model to follow the drawing;
- **a Warli LoRA**, a small style adapter we trained ourselves on 45 Warli images on a free Google Colab GPU (1500 steps, about 10 minutes);
- **LCM-LoRA**, which cuts sampling to 6 steps so it runs on a CPU;
- **circular padding** for repeats, so every convolution wraps around the edges and the painted tile wraps too.

Diffusion runs at no more than 768 pixels. The final print files are drawn from vectors, never upscaled.

### 2.5 Survival check and repair (chhaap/studio.py)

Diffusion sometimes loses or changes symbols. After painting, each placed symbol is compared with the output inside its box (intersection over union of inked pixels, after a 1-pixel widening; 0.5 or more counts as present).

If a hero or support symbol is lost:
1. rerun with ControlNet 0.15 stronger (at most twice), keeping the best pass;
2. if still lost, paste the clean vector symbol back in its box.

The meaning card then splits symbols into "present in this design" and "placed but lost", so it never describes something that is not on the print.

### 2.6 Colour, texture, products (chhaap/palette.py, chhaap/products.py)

- **Colour:** each element belongs to a layer (ground, figure ink, accent, border, filler). Eight palettes assign a colour per layer: four traditional (white on geru, maroon, indigo, charcoal) and four contemporary. After diffusion, the output is traced into vector curves and each curve takes the layer of the element it covers, so recolouring is exact.
- **Texture:** blurred noise multiplied over the ground and uneven paint opacity, on raster files only.
- **Products:** frame A4/A3, saree set (body tile, border strip, pallu), diary wrap (back, spine, front), wallpaper, two phone sizes, tee. Mockups are drawn in code from flat shapes; no stock photos.
- **Labels:** every file carries "AI-generated, Warli-inspired. Not a GI-certified Warli painting." (Mandana and fusion designs get their own label.)

## 3. Tech stack

| Part | Tool | Why |
|:--|:--|:--|
| Language | Python 3.12 | Standard for ML; one language for model, app and analysis |
| Image model | Stable Diffusion 1.5 (Hugging Face diffusers) | Open weights, small enough for a CPU, mature ControlNet and LoRA support |
| Layout control | ControlNet scribble (lllyasviel) | Makes the model follow our drawing |
| Style | Warli LoRA trained with diffusers' LoRA script on Colab | Free GPU; the laptop has no NVIDIA GPU |
| Speed | LCM-LoRA, TAESD | 6 steps instead of 25 on CPU; TAESD gives cheap step previews |
| Deep learning | PyTorch (CPU) | Required by diffusers |
| Vector tracing | potracer (pure Python Potrace) | Print files from curves; no system install needed |
| Plan validation | pydantic | Rejects plans that name unknown symbols |
| Metrics | scipy, scikit-learn, torchmetrics, CLIP | Statistics, CLIP probe, KID |
| Web app | FastAPI + one HTML, CSS and JS file, SQLite | Simple, local, no build step |
| Paper | LaTeX (IEEEtran), compiled with tectonic | IEEE format |
| Docs | pandoc, python-docx, LibreOffice | Synopsis on the college template, paper as .docx |

Hardware: Intel Core Ultra 7 155H laptop, 15 GB RAM, no usable GPU. Everything runs locally and is free; the only external step was LoRA training on free Colab.

## 4. Where the code lives

| File | Role |
|:--|:--|
| chhaap/compose.py | Lexicon loading, the drawing-recipe interpreter, v1 tile composer |
| chhaap/layout.py | Layout engine: templates, borders, fillers, repeats, overlap checks |
| chhaap/planner.py | Brief to plan (rules, Ollama, Claude) with validation |
| chhaap/generate.py | Diffusion pipeline, circular padding, step previews |
| chhaap/studio.py | Stylize, survival check, repair, layered tracing |
| chhaap/palette.py | Palettes, colourizing, texture |
| chhaap/products.py | Products, assembly, mockups, export |
| chhaap/meaning.py | Meaning card and story caption |
| chhaap/metrics.py | Seam metric (SDR), KID, CLIP probe |
| app.py, static/ | The local web app |
| scripts/ | Data preparation, experiments, summary, number and prose checks |
| eval/summary.md | Every result, generated by a script from eval/results/*.json |
| paper/, synopsis/ | IEEE paper and synopsis |

Every module has a self-check you can run, for example `.venv/bin/python -m chhaap.layout`.

## 5. What was measured

All numbers come from eval/summary.md. N = 16 per condition on this CPU.

### First version (single tiles)
- **E1 tiling:** mean seam score could not separate conditions, because framed tiles push it below 1 and broken seams above. A log version of the score (defined after seeing the data, reported as post hoc) showed that circular padding removes framing: the LoRA alone gave the worst score (1.247), LoRA with circular padding 0.147 (p = 0.0001).
- **E2 style:** a CLIP probe and KID disagreed about which output looks most like Warli.
- **E5 cost:** a composed tile takes about 36 seconds on the CPU.

### Second version (product designs)
- **E7 symbol survival:** across 16 pages (852 symbols), diffusion kept 0.587 of hero and support symbols on its first pass. Symbols with more drawing primitives were lost more often (rho = -0.474, p = 0.0349), but this is fragile. The strongest effect: rotated ring dancers survived 0.468 against 0.828 for upright symbols (post hoc; confounded with crowding).
- **E8 layout:** all four templates spread ink more evenly than random scatter. Without fillers, the medallion is no better than scatter, so its evenness comes from fillers; registers and buti stay better on structure alone.
- **E9 diffusion's cost:** vector only takes 0.152 s and keeps every symbol; diffusion alone keeps 0.587 in 67.7 s; with repair 1.000 in 141.2 s per page.
- **E10 planner:** the rules planner met 0.944 of 71 stated constraints in 20 fixed briefs. This is optimistic because the same person wrote the briefs and the rules.
- **Not run:** the human studies (E3, E4, and the E8/E9 preferences), the Ollama and Claude planners, and a Mandana LoRA.

## 6. Problems found and fixed during the build

These are real iterations (full list in docs/CHANGELOG.md). They are good to mention, because they show the system was tested, not just written.

- The first CPU outputs were black ink on peach; ControlNet strength and the prompt were tuned on seeds outside the test seeds.
- A blank page margin came back from the model as paper and was traced as ink; pages are now cropped to their drawn area first.
- PIL rounds negative coordinates differently, so half-drop tiles were off by one pixel at the edge; drawing moved to a padded canvas.
- The repair loop kept the last pass even when a stronger ControlNet made things worse; it now keeps the best pass.
- The medallion and registers templates silently skipped some planned symbols while the meaning card said "8 of 8"; a self-test now checks that every planned symbol is placed, and the card counts unplaced symbols as lost. E7 and E8 were rerun.
- The Kaggle "mandana" class turned out to be mostly mandala pen drawings, a different art; cleaning kept 23 of 140 images.

## 7. Honesty rules the project follows

- Every number in the paper comes from a results file; a script (scripts/check_numbers.py) checks this before compiling.
- Every symbol meaning has a source URL; none is verified by an artist, and the card says so.
- Experiments that did not run are reported as not run.
- Post-hoc analyses are labelled post hoc.
- Training data were scraped by a third party with no clear licence, so they are used for research only. The trained adapter is in the repository for research use under the same caveat; the training images are not.
- Warli has a Geographical Indication (2014). Outputs are labelled as AI-generated and not GI-certified.

## 8. Questions to expect

**Why not just ask an image model for a Warli design?**
It draws framed pictures that do not tile, and it cannot tell you which symbols it drew. Placing symbols first solves both.

**What exactly does the AI do here?**
Three things: the LoRA-adapted Stable Diffusion paints the line quality; ControlNet makes it follow our layout; optionally a language model turns the brief into a plan. Structure, colour, symbol choice and meanings come from our own code and data.

**What did you train?**
The Warli LoRA: 45 cleaned Warli images, BLIP captions with a trigger word, rank 16, 1500 steps on a free Colab GPU. The cleaning pipeline (deduplication, size filter, CLIP filter, manual review) is in scripts/prepare_data.py.

**How do you know the meaning card is correct?**
It lists exactly the symbols the layout engine placed and the survival check confirmed, with meanings copied from sourced lexicon rows. It cannot catch an artist's disagreement with a source, which is why it says the meanings are not yet verified by a Warli artist.

**What is circular padding?**
Convolutions normally pad the image edge with zeros. Circular padding pads with pixels from the opposite edge, so the network treats the image as a torus and the output wraps.

**Does diffusion actually improve the design?**
Unproven. It costs time and loses symbols that repair must restore. What it adds is the hand-painted line, which our metrics do not measure; the blind preference test that would decide it has not been run.

**Why a CPU?**
That is the hardware available. LCM-LoRA (6 steps) and a 768-pixel limit keep a design to a few minutes.

**What about the artists?**
The paper proposes a licensing model: a LoRA trained only on work that Warli artists license, with royalties per design. It has not been tested.

## 9. How to demo

1. Start the app: `.venv/bin/python -m app`, open http://localhost:7860.
2. Open the Gallery tab: pre-rendered designs for every product, a Mandana design, a fusion design and two hand-painted frames.
3. Click one, then show Under the hood (planner, layout, denoising steps, survival table, timing) and the Meaning card.
4. For a live run, pick an example brief, set Press settings to Vector only, press Print design (about one second). A hand-painted run takes 2 to 4 minutes; talk through the Gallery while it runs. Run only one hand-painted print at a time.
