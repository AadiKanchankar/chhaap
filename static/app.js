const $ = (s) => document.querySelector(s);
const api = async (url, body) => {
  const r = await fetch(url, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `${r.status} ${r.statusText}`);
  return r.json();
};
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) k === "style" ? n.style.cssText = v : k in n ? n[k] = v : n.setAttribute(k, v);
  n.append(...kids.filter((k) => k != null));
  return n;
};
const fmt = (x, d = 2) => (x == null ? "-" : Number(x).toFixed(d));
const symMask = (id) => `--m:url(/api/symbol/${id}.png)`;

function tabs(list) {
  const btns = [...list.querySelectorAll('[role="tab"]')];
  const show = (b) => {
    btns.forEach((x) => { const on = x === b; x.setAttribute("aria-selected", on); x.tabIndex = on ? 0 : -1; $("#" + x.getAttribute("aria-controls")).hidden = !on; });
    b.dispatchEvent(new CustomEvent("shown", { bubbles: true }));
  };
  btns.forEach((b, i) => {
    b.onclick = () => show(b);
    b.onkeydown = (e) => {
      const j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: btns.length - 1 }[e.key];
      if (j !== undefined) { e.preventDefault(); const t = btns[(j + btns.length) % btns.length]; t.focus(); show(t); }
    };
  });
  return show;
}

/* ---------------- studio (v2): brief -> plan -> product design ---------------- */
const S = { opt: null, product: "frame_a4", plan: null, planner: null, mode: "stylized", design: null };
const EXAMPLES = [
  ["Anniversary frame", "A3 frame for my parents' anniversary. Wedding and harvest, maroon and mustard, busy, traditional border.", "frame_a3"],
  ["Forest saree", "Saree with forest animals and peacocks, forest green and saffron, a chain of dancers on the border.", "saree"],
  ["Village diary", "Diary cover about village life, mustard and rust, calm and minimal.", "diary"],
  ["Tarpa phone", "Phone wallpaper of the tarpa dance in rings, white on charcoal.", "phone"],
];
const NAMES = { tarpa_spiral: "Tarpa spiral", registers: "Registers", medallion: "Medallion", all_over_buti: "All-over buti", mandana_medallion: "Mandana rings", dehri: "Threshold band (Mandana)", lotus: "Lotus band (Mandana)",
  straight: "Straight", half_drop: "Half-drop", brick: "Brick", sparse: "Sparse", balanced: "Balanced", dense: "Dense",
  triangles: "Triangles", chevrons: "Chevrons", dots: "Dots", vine: "Leaf vine", dancers: "Chain of dancers" };
const ICONS = {  // drawn product glyphs, 40x40, one stroke weight
  frame: '<rect x="9" y="4" width="22" height="32"/><rect x="13" y="8" width="14" height="24"/><path d="M16 26l4-7 4 7z"/>',
  saree: '<path d="M3 14h34v13H3z"/><path d="M3 17h34M3 24h34M27 14v13"/><path d="M30 18l2 3-2 3-2-3z"/>',
  diary: '<rect x="10" y="5" width="21" height="30"/><path d="M14 5v30M10 9h-2M10 31h-2"/><circle cx="23" cy="18" r="4"/>',
  wallpaper: '<rect x="5" y="5" width="30" height="30"/><path d="M12 10l3 4-3 4-3-4zM28 10l3 4-3 4-3-4zM20 20l3 4-3 4-3-4z"/>',
  phone: '<rect x="13" y="4" width="15" height="32"/><path d="M18 7h5"/><circle cx="20.5" cy="20" r="4"/>',
  tee: '<path d="M14 6l-9 6 4 6 4-3v19h15V15l4 3 4-6-9-6c-1 3-3 4-6.5 4S15 9 14 6z"/>',
};
const iconFor = (id) => ICONS[id.startsWith("frame") ? "frame" : id];
const svg = (inner) => { const t = document.createElement("template"); t.innerHTML = `<svg viewBox="0 0 40 40" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`; return t.content.firstChild; };

function seg(box, values, current, onpick) {
  box.replaceChildren(...values.map((v) => el("button", { type: "button", role: "radio", "aria-checked": v === current, onclick: (e) => { box.querySelectorAll("button").forEach((b) => b.setAttribute("aria-checked", b === e.currentTarget)); onpick(v); } }, NAMES[v] || v)));
}
const status = (msg, err) => { $("#status").textContent = msg; $("#status").classList.toggle("err", !!err); };

async function workbench() {
  S.showTab = tabs($("#workbench .tabs"));
  const [opt, m] = await Promise.all([api("/api/v2/options"), api("/api/machine")]);
  S.opt = opt;
  S.sym = Object.fromEntries(opt.symbols.map((x) => [x.id, x.name]));
  S.symOptions = () => ["warli", "mandana"].map((pk) => el("optgroup", { label: pk === "warli" ? "Warli" : "Mandana" },
    ...opt.symbols.filter((x) => x.pack === pk).map((x) => el("option", { value: x.id }, x.name))));
  $("#machine").textContent = `${m.device.toUpperCase()} · ${m.fast ? "LCM, " + m.steps + " steps" : m.steps + " steps"} · Warli LoRA ${m.lora ? "loaded" : "not trained yet"} · planner: ${opt.backends.at(-1)}`;
  $("#steps").value = m.steps; $("#cfg").value = m.cfg; $("#cn").value = $("#cn-out").value = m.cn;
  if (!m.lora) { $("#lora").disabled = true; $("#lora-out").value = "off"; $("#lora-hint").textContent = "not trained yet"; }
  for (const [inp, out] of [["#lora", "#lora-out"], ["#cn", "#cn-out"]]) $(inp).oninput = () => ($(out).value = $(inp).value);
  $("#reseed").onclick = () => ($("#seed").value = Math.floor(Math.random() * 10000));
  $("#mode").querySelectorAll("button").forEach((b) => (b.onclick = () => { S.mode = b.dataset.v; $("#mode").querySelectorAll("button").forEach((x) => x.setAttribute("aria-checked", x === b)); }));

  $("#examples").replaceChildren(...EXAMPLES.map(([name, text, prod]) => el("button", { type: "button", className: "chip", onclick: () => { $("#brief").value = text; pickProduct(prod, false); readBrief(); } }, name)));
  $("#products").replaceChildren(...opt.products.map((p) => el("button", { type: "button", className: "product", role: "radio", "aria-checked": p.id === S.product, "data-id": p.id, title: p.note, onclick: () => pickProduct(p.id, true) },
    svg(ICONS[p.id.startsWith("frame") ? "frame" : p.id]), el("span", {}, p.name), el("small", {}, p.id === "frame_a3" ? "A3, 297 x 420 mm" : p.id === "frame_a4" ? "A4, 210 x 297 mm" : p.note))));
  pickProduct(S.product, false);
  $("#read").onclick = readBrief;
  $("#brief").onkeydown = (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) readBrief(); };
  $("#add-beat").onclick = () => { if (S.plan.story_beats.length < 4) { S.plan.story_beats.push({ beat: "new beat", symbol_ids: ["tree"] }); drawPlan(); } };
  $("#border").onchange = () => (S.plan.border_style = $("#border").value || null);
  $("#hero").onchange = () => (S.plan.hero_symbol_id = $("#hero").value);
  $("#print").onclick = printDesign;
  $("#do-export").onclick = doExport;
  $("#workbench").addEventListener("shown", (e) => {
    const id = e.target.id;
    if (id === "t-hood") hood();
    if (id === "t-repeat") repeatView();
    if (id === "t-meaning") meaningView();
    if (id === "t-gallery") gallery();
  });
  const h = new URLSearchParams(location.hash.slice(1));  // #design=<id>&tab=<tab id>: reopen after reload
  if (h.get("design")) { try { showDesign(await api(`/api/v2/designs/${h.get("design")}`)); } catch (e) { status(`Could not reopen design ${h.get("design")}: ${e.message}`, true); } }
  else { $("#brief").value = EXAMPLES[0][1]; pickProduct(EXAMPLES[0][2], false); await readBrief(); }
  if (h.get("tab") && $("#" + h.get("tab"))) S.showTab($("#" + h.get("tab")));
  if (h.get("press") === "open") $("#press-settings").open = true;
}

function pickProduct(id, replan) {
  S.product = id;
  document.querySelectorAll(".product").forEach((b) => b.setAttribute("aria-checked", b.dataset.id === id));
  $("#product-note").textContent = S.opt.products.find((p) => p.id === id).note;
  if (replan && S.plan) readBrief();
}

async function readBrief() {
  const b = $("#read"); b.disabled = true;
  try {
    const r = await api("/api/v2/plan", { brief: $("#brief").value, product: S.product });
    S.plan = r.plan; S.planner = r;
    $("#planner-hint").textContent = `Planned by ${r.backend}${r.fallback ? ` (fell back from ${r.requested})` : ""} in ${(r.seconds * 1000).toFixed(0)} ms.`;
    drawPlan();
  } catch (e) { $("#planner-hint").textContent = `Could not read the brief: ${e.message}`; }
  b.disabled = false;
}

function drawPlan() {
  const p = S.plan;
  $("#plan").disabled = false;
  seg($("#tpl"), S.opt.templates, p.template, (v) => { p.template = v; p.repeat = v === "all_over_buti" ? p.repeat || "half_drop" : null; drawPlan(); });
  $("#repeat-row").hidden = p.template !== "all_over_buti";
  seg($("#rep"), ["straight", "half_drop", "brick"], p.repeat, (v) => (p.repeat = v));
  seg($("#dens"), S.opt.densities, p.density, (v) => (p.density = v));
  $("#pal").replaceChildren(...S.opt.palettes.map((c) => el("button", { type: "button", role: "radio", className: "swatch", "aria-checked": c.id === p.palette_id, title: c.name,
    onclick: () => { p.palette_id = c.id; drawPlan(); } },
    el("span", { className: "chips5" }, ...["ground", "ink", "accent", "border"].map((k) => el("i", { style: `background:${c[k]}` }))), el("small", {}, c.name))));
  $("#border").replaceChildren(el("option", { value: "" }, "No border"), ...S.opt.borders.map((b) => el("option", { value: b, selected: b === p.border_style }, NAMES[b])));
  $("#hero").replaceChildren(...S.symOptions());
  $("#hero").value = p.hero_symbol_id;
  $("#beats").replaceChildren(...p.story_beats.map((b, i) => el("li", {},
    el("div", { className: "beat-head" },
      el("input", { type: "text", value: b.beat, "aria-label": `Beat ${i + 1} name`, oninput: (e) => (b.beat = e.target.value) }),
      p.story_beats.length > 1 ? el("button", { type: "button", className: "x", "aria-label": `Remove beat ${b.beat}`, onclick: () => { p.story_beats.splice(i, 1); drawPlan(); } }, svg('<path d="M12 12l16 16M28 12L12 28"/>')) : null),
    el("div", { className: "beat-syms" },
      ...b.symbol_ids.map((id, j) => el("button", { type: "button", className: "sym-chip", title: `Remove ${S.sym[id]}`, "aria-label": `Remove ${S.sym[id]} from ${b.beat}`,
        onclick: () => { if (b.symbol_ids.length > 1) { b.symbol_ids.splice(j, 1); drawPlan(); } } }, el("i", { style: symMask(id), "aria-hidden": "true" }), S.sym[id])),
      el("select", { "aria-label": `Add a symbol to ${b.beat}`, onchange: (e) => { if (e.target.value) { b.symbol_ids.push(e.target.value); drawPlan(); } } },
        el("option", { value: "" }, "Add symbol"), ...S.symOptions())))));
  $("#add-beat").hidden = p.story_beats.length >= 4;
}

async function printDesign() {
  if (!S.plan) return status("Read the brief first.", true);
  const b = $("#print"); b.disabled = true;
  $("#strip").replaceChildren();
  try {
    const { id } = await api("/api/v2/design", { plan: S.plan, brief: $("#brief").value, planner: S.planner, mode: S.mode, seed: +$("#seed").value,
      steps: +$("#steps").value, cfg: +$("#cfg").value, lora_scale: $("#lora").disabled ? null : +$("#lora").value, cn_scale: +$("#cn").value, texture: $("#texture").checked });
    const t0 = performance.now();
    for (;;) {
      await new Promise((r) => setTimeout(r, 1000));
      const d = await api(`/api/v2/designs/${id}`);
      const secs = ((performance.now() - t0) / 1000).toFixed(0);
      if (d.status.startsWith("error")) throw new Error(d.status.slice(7));
      fillStrip(d.steps);
      if (d.status === "done") {
        showDesign(d); status(`Design ${id.slice(2)} printed in ${d.timing.total.toFixed(1)} s.`);
        if (matchMedia("(max-width: 900px)").matches) $("#mock-wrap").scrollIntoView({ behavior: "smooth", block: "start" });  // phones: the plan sits above
        break;
      }
      status(d.status === "queued" ? "Waiting for the press." : d.status.startsWith("stylizing") ? `Painting the ${d.status.slice(10)} part: ${d.steps.length ? `step ${d.steps.length}` : "loading models"} (${secs} s)` : `${d.status} (${secs} s)`);
    }
  } catch (e) { status(`The press stopped: ${e.message}`, true); }
  b.disabled = false;
}

function fillStrip(steps) {
  const strip = $("#strip");
  for (let i = strip.children.length; i < steps.length; i++) strip.append(el("li", {}, el("img", { src: `/runs/${steps[i]}`, alt: `Step ${i + 1} preview`, width: 72, height: 72 }), `Step ${i + 1}`));
}

function showDesign(d) {
  S.design = d;
  history.replaceState(null, "", `#design=${d.id}`);
  if (d.plan) { S.plan = structuredClone(d.plan); pickProduct(d.plan.product, false); drawPlan(); }
  if (d.brief !== undefined) $("#brief").value = d.brief;
  $("#strip").replaceChildren(); fillStrip(d.steps || []);
  const img = $("#mockup");
  img.src = `/runs/${d.id}/mockup.png?${Date.now()}`; img.hidden = false; $("#mock-empty").hidden = true;
  img.classList.remove("stamped"); void img.offsetWidth; img.classList.add("stamped");
  $("#caption").textContent = d.caption || "";
  const s = d.survival, kept = d.card.symbols.length, all = kept + d.card.lost.length;
  const cells = [["Design no.", d.id.slice(2)], ["Product", S.opt.products.find((p) => p.id === d.plan.product).name], ["Layout", NAMES[d.plan.template]],
    ["Palette", S.opt.palettes.find((p) => p.id === d.plan.palette_id).name], ["Rendering", d.mode === "vector" ? "vector only" : "hand-painted"],
    ["Symbols present", `${kept} of ${all}`], ["Symbols repaired", d.mode === "vector" ? "-" : `${s.repaired_rerun + s.repaired_vector} of ${s.checked}`], ["Density", NAMES[d.plan.density]], ["Seconds", d.timing.total.toFixed(1)]];
  $("#readout").replaceChildren(...cells.map(([k, v]) => el("div", {}, el("dt", {}, k), el("dd", {}, String(v)))));
  $("#deliverables").replaceChildren(...d.previews.map((f) => el("figure", {}, el("img", { src: `/runs/${d.id}/${f}`, alt: f.replace("preview_", "").replace(".png", "").replace("_", " "), loading: "lazy" }),
    el("figcaption", {}, f.replace("preview_", "").replace(".png", "").replace("_", " ")))));
  $("#files").replaceChildren();
}

const STAGES = {
  planner: ["Planner", "The brief is turned into a plan: product, layout, story beats, palette, density. The rules backend matches words; a local language model can stand in when Ollama is installed. Either way the plan may only name symbols from the lexicon, and a plan that names anything else is rejected."],
  layout: ["Layout", "The layout engine places the hero, the supporting scenes and the fillers at product size, sizing them hero, support and filler in a ratio of about 8 to 3 to 1. It records the role and colour layer of every element, so colour is exact later. This is the drawing ControlNet follows."],
  denoise: ["Denoising", "Diffusion paints only the line quality: the monochrome drawing goes through Stable Diffusion 1.5 with the scribble ControlNet and the Warli LoRA, at no more than 768 pixels. These are TAESD previews of each LCM step."],
  survival: ["Survival check", "Every placed symbol is compared with the output inside its box (overlap of the inked pixels, after a one-pixel widening). Below 0.5 the symbol counts as lost. A lost hero or support symbol triggers a rerun with ControlNet 0.15 stronger, twice at most, and then the clean vector symbol is put back in its box."],
  recolour: ["Recolour and texture", "The repaired ink is traced into curves. Each curve takes the colour layer of the element it overlaps, so ground, figures, hero accent, border and fillers get exact palette colours. A mud-wall grain is added to raster files only."],
  timing: ["Timing", "Where the seconds went on this machine."],
};

function hood() {
  const d = S.design, list = $("#stages");
  if (!d) return list.replaceChildren(el("li", { className: "empty" }, "Print a design first; each stage of it will be laid out here."));
  const pl = d.planner || {};
  const stage = (k, ...art) => el("li", { className: "stage" }, el("div", {}, el("h3", {}, STAGES[k][0]), el("p", {}, STAGES[k][1])), el("div", { className: "art" }, ...art));
  const parts = d.parts.filter((p) => p.stylize && d.mode !== "vector");
  const rows = [stage("planner", el("p", { className: "mono" }, `brief: ${d.brief || "(none)"}`),
    el("p", { className: "mono" }, `backend: ${pl.backend || "edited by hand"}${pl.seconds != null ? `, ${(pl.seconds * 1000).toFixed(0)} ms` : ""}${pl.usage?.tokens_out ? `, ${pl.usage.tokens_in} + ${pl.usage.tokens_out} tokens` : ""}`),
    el("pre", { className: "mono plan-json" }, JSON.stringify(d.plan, null, 1)))];
  rows.push(stage("layout", ...(parts.length ? parts.map((p) => el("figure", {}, el("img", { src: `/runs/${d.id}/${p.name}/control.png`, alt: `Control image, ${p.name}` }), el("figcaption", { className: "mono" }, `${p.name}: ink coverage ${(100 * d.coverage[p.name]).toFixed(1)}%`)))
    : [el("p", { className: "mono" }, Object.entries(d.coverage).map(([k, v]) => `${k}: ink coverage ${(100 * v).toFixed(1)}%`).join("\n"))])));
  if (parts.length) {
    rows.push(stage("denoise", el("div", { className: "film" }, ...d.steps.map((s, i) => el("img", { src: `/runs/${s}`, alt: `Step ${i + 1}` }))),
      ...parts.map((p) => el("img", { src: `/runs/${d.id}/${p.name}/stylized.png`, alt: `Stylized ${p.name}` }))));
    rows.push(stage("survival", ...parts.map((p) => el("div", {}, el("p", { className: "mono" }, `${p.name}: ` + d.attempts[p.name].map((a, i) => `pass ${i + 1} ControlNet ${a.cn_scale}, ${a.lost_main} main lost, ${(100 * a.survival_rate).toFixed(0)}% kept, ${a.seconds.toFixed(0)} s`).join("; ")),
      survivalTable(d.elements.filter((e) => e.part === p.name))))));
    rows.push(stage("recolour", ...parts.map((p) => el("img", { src: `/runs/${d.id}/${p.name}/ink.png`, alt: `Repaired ink, ${p.name}` })), el("img", { src: `/runs/${d.id}/${d.previews[0]}`, alt: "Recoloured preview" })));
  } else {
    rows.push(el("li", { className: "stage" }, el("div", {}, el("h3", {}, "No diffusion"), el("p", {}, "This design was rendered vector only: the layout itself, recoloured by layer. Every placed symbol is present by construction.")), el("div", { className: "art" }, el("img", { src: `/runs/${d.id}/${d.previews[0]}`, alt: "Vector preview" }))));
  }
  rows.push(stage("timing", timing(d.timing)));
  list.replaceChildren(...rows);
}

function survivalTable(els) {
  const main = els.filter((e) => e.role !== "filler");
  const fillers = els.filter((e) => e.role === "filler");
  return el("table", { className: "mono surv" }, el("thead", {}, el("tr", {}, ...["symbol", "role", "first IoU", "final IoU", "path"].map((h) => el("th", {}, h)))),
    el("tbody", {}, ...main.map((e) => el("tr", { className: e.path }, el("td", {}, S.sym[e.sid]), el("td", {}, e.role), el("td", {}, fmt(e.iou0)), el("td", {}, fmt(e.iou)), el("td", {}, e.path.replace("_", " ")))),
      fillers.length ? el("tr", {}, el("td", { colSpan: 5 }, `${fillers.length} fillers: ${fillers.filter((e) => e.survived).length} kept, not repaired`)) : null));
}

function timing(t) {
  const rows = Object.entries(t).filter(([k]) => k !== "total");
  const max = Math.max(...rows.map((x) => x[1]));
  return el("div", { className: "timing" }, ...rows.map(([k, v]) => el("div", {}, el("span", {}, k.replace(/_/g, " ")), el("b", { style: `width:${(100 * v) / max}%` }), el("span", {}, `${v.toFixed(2)} s`))),
    el("div", {}, el("span", {}, "total"), el("span", {}, ""), el("span", {}, `${t.total.toFixed(2)} s`)));
}

function repeatView() {
  const d = S.design, box = $("#repeat-box");
  if (!d) return box.replaceChildren(el("p", { className: "empty" }, "Print a design first."));
  const tile = { wallpaper: "preview_tile.png", saree: "preview_body_tile.png" }[d.plan.product] || (d.parts.some((p) => p.repeat) && d.plan.product === "tee" ? "preview_print.png" : null);
  if (!tile && d.plan.product !== "diary") return box.replaceChildren(el("p", { className: "note" }, `A ${S.opt.products.find((p) => p.id === d.plan.product).name.replace(/^\w/, (ch) => ch.toLowerCase())} is a single composition with a border, so it does not repeat. Wallpaper, the saree body and the diary back are the repeating products.`));
  const src = tile ? `/runs/${d.id}/${tile}` : `/runs/${d.id}/preview_wrap.png`;
  const rep = d.parts.find((p) => p.repeat)?.repeat;
  box.replaceChildren(el("div", { className: "repeat", style: `background-image:url(${src})` }),
    el("p", { className: "note" }, `${NAMES[rep] || "Straight"} repeat, shown three tiles across. The tile wraps because the layout engine draws every motif with its copies across each edge, and diffusion ran with circular padding, so the painted line wraps too.`));
}

function renderCard(c, box) {
  const entry = (s) => el("article", {},
    el("i", { style: symMask(s.id), "aria-hidden": "true" }),
    el("div", {}, el("h3", {}, s.name, s.local_name ? el("small", {}, s.local_name) : null, s.count > 1 ? el("small", {}, `x${s.count}`) : null),
      el("p", {}, s.meaning), el("p", { className: "ctx" }, s.context), el("p", { className: "src" }, "Source: ", el("a", { href: s.source_url, target: "_blank", rel: "noopener" }, new URL(s.source_url).hostname.replace(/^www\./, "")))));
  const kids = [];
  if (c.fusion_note) kids.push(el("p", { className: "note" }, c.fusion_note));
  const split = c.lost !== undefined;  // study cards (v1 tiles) have no survival check
  if (split) kids.push(el("h3", { className: "card-h" }, "Present in this design"));
  const packs = [...new Set(c.symbols.map((s) => s.pack))];
  for (const pk of packs) {
    if (split) kids.push(el("h4", { className: "pack" }, pk === "mandana" ? "Mandana" : "Warli"));
    kids.push(...c.symbols.filter((s) => s.pack === pk).map(entry));
  }
  if (split) kids.push(el("section", { className: "lost" }, el("h3", { className: "card-h" }, "Placed but lost in generation"), el("p", { className: "note" }, c.lost_note), ...c.lost.map(entry)));
  kids.push(el("footer", {}, c.footer));
  box.replaceChildren(...kids);
}

function meaningView() {
  if (S.design) renderCard(S.design.card, $("#card"));
}

const FILE_NOTE = { design: "print, 300 DPI", body_tile: "repeat tile, 300 DPI", border: "border strip, 300 DPI", pallu: "pallu panel, 300 DPI", wrap: "A5 wrap, 300 DPI",
  tile: "repeat tile, 300 DPI", "1290x2796": "phone screen", "1080x2400": "phone screen", print: "4500 x 5400 at 300 DPI", mockup: "mockup" };

const exportStatus = (msg, err) => { $("#export-status").textContent = msg; $("#export-status").classList.toggle("err", !!err); };

async function doExport() {
  if (!S.design) return exportStatus("Print a design first.", true);
  exportStatus("Drawing the print files at 300 DPI. A3 and tee files take up to a minute.");
  const b = $("#do-export"); b.disabled = true; b.textContent = "Drawing print files";
  try {
    const f = await api(`/api/v2/designs/${S.design.id}/export`, {});
    $("#files").replaceChildren(...Object.entries(f).map(([k, url]) => el("li", {}, el("a", { href: url, download: "" },
      el("img", { src: url, alt: "", loading: "lazy" }), el("span", {}, k.replace(/_svg$/, " (vector)").replace(/_/g, " ")),
      el("small", {}, k.endsWith("_svg") ? "SVG, any size" : FILE_NOTE[k] || "PNG")))));
    exportStatus(`${Object.keys(f).length} files ready. Each carries the AI-generated label.`);
  } catch (e) { exportStatus(`Export failed: ${e.message}. Check that the design finished printing, then try again.`, true); }
  b.disabled = false; b.textContent = "Prepare print files";
}

async function gallery() {
  const g = await api("/api/v2/gallery");
  const box = $("#gallery");
  if (!g.length) return box.replaceChildren(el("li", { className: "empty" }, "Nothing printed yet. Every design you print appears here on its mockup."));
  box.replaceChildren(...g.map((d) => el("li", {}, el("button", { type: "button", onclick: async () => { showDesign(await api(`/api/v2/designs/${d.id}`)); S.showTab($("#t-design")); } },
    el("img", { src: d.mockup, alt: "", loading: "lazy" }), el("span", {}, d.brief || "(no brief)"),
    el("small", {}, `${S.opt.products.find((p) => p.id === d.product).name} · ${d.mode === "vector" ? "vector only" : "hand-painted"} · no. ${d.id.slice(2)}`)))));
}

/* ---------------- study (/study) ---------------- */
async function study() {
  $("#workbench").hidden = true; $("#study").hidden = false;
  tabs($("#study .tabs"));
  $("#study").addEventListener("shown", (e) => (e.target.id === "t-anno" ? annotate() : e.target.id === "t-designs" ? pair2() : pair()));
  pair();
}

async function pair() {
  const st = $("#pref-status");
  let p;
  try { p = await api("/api/study/pair"); } catch (e) { st.textContent = `No pairs to show yet: ${e.message}.`; return; }
  const order = p.left === "a" ? [p.a_run, p.e_run] : [p.e_run, p.a_run];
  const vote = { seed: p.seed, a_run: p.a_run, e_run: p.e_run, left: p.left };
  const cond = (side) => (side === "left") === (p.left === "a") ? "a" : "e";
  $("#after").hidden = true;
  $("#pair").replaceChildren(...order.map((rid, i) => el("figure", { className: "plate" },
    el("button", { type: "button", onclick: (ev) => { vote.choice = cond(i ? "right" : "left"); ev.currentTarget.classList.add("chosen"); afterCard(p, vote); } },
      el("img", { src: `/runs/${rid}/tile.png`, alt: `${i ? "Right" : "Left"} pattern`, width: 512, height: 512 })),
    el("figcaption", {}, i ? "Right" : "Left"))));
  st.textContent = "";
}

function afterCard(p, vote) {
  document.querySelectorAll("#pair button").forEach((b) => (b.disabled = true));
  const side = p.left === "e" ? "left" : "right";
  renderCard(p.meaning, $("#pair-card"));
  $("#pair-card").prepend(el("p", { className: "lede" }, `Meaning card for the ${side} pattern`));
  $("#after").hidden = false;
  const send = async (s) => {
    vote.choice_after_card = (s === "left") === (p.left === "a") ? "a" : "e";
    const r = await api("/api/study/vote", vote);
    $("#pref-status").textContent = `Saved. ${r.n} answers so far.`;
    window.scrollTo({ top: 0 });
    pair();
  };
  $("#after-left").onclick = () => send("left");
  $("#after-right").onclick = () => send("right");
}

async function pair2() {
  const st = $("#pref2-status");
  st.textContent = "Drawing the next pair.";
  let p;
  try { p = await api("/api/study/pair2"); } catch (e) { st.textContent = `No pairs to show yet: ${e.message}.`; return; }
  const vote = async (side) => {
    document.querySelectorAll("#pair2 button").forEach((b) => (b.disabled = true));
    const r = await api("/api/study/pref2", { kind: p.kind, item: p.item, left: p.left, treat: p.treat, choice: side === "left" ? p.left : p.right });
    st.textContent = `Saved. ${r.n} answers so far.`;
    pair2();
  };
  $("#pair2").replaceChildren(...[["left", p.left_src], ["right", p.right_src]].map(([side, src]) => el("figure", { className: "plate" },
    el("button", { type: "button", onclick: () => vote(side) }, el("img", { src, alt: `${side} design` })), el("figcaption", {}, side === "left" ? "Left" : "Right"))));
  st.textContent = "";
}

async function annotate() {
  const a = await api("/api/study/annotate"), box = $("#anno");
  if (a.done) return box.replaceChildren(el("p", { className: "lede" }, `All images annotated (${a.n}). Thank you.`));
  const form = el("fieldset", {}, el("legend", {}, "Tick each symbol you can see in the image"),
    ...a.symbols.map((s) => el("label", {}, el("input", { type: "checkbox", name: s.id }), s.name)),
    el("div", { className: "press" }, el("button", { type: "button", className: "stamp", onclick: async (ev) => {
      ev.currentTarget.disabled = true;
      const present = Object.fromEntries(a.symbols.map((s) => [s.id, form.querySelector(`[name="${s.id}"]`).checked]));
      await api("/api/study/annotate", { run: a.run, present });
      $("#anno-status").textContent = `Saved. ${a.remaining - 1} images left.`;
      annotate();
    } }, "Save and next")));
  box.replaceChildren(el("img", { src: `/runs/${a.run}/tile.png`, alt: "Image to annotate", width: 512, height: 512 }), form);
}

location.pathname.startsWith("/study") ? study() : workbench();
