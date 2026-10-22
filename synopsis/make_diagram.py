from PIL import Image, ImageDraw, ImageFont
import glob
f = lambda s: ImageFont.truetype((glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True) or [None])[0], s)
boxes = [
 ("Story", "harvest, wedding, tarpa,\nvillage day, forest"),
 ("Composer", "lexicon symbols on a\ntoroidal canvas"),
 ("Generator", "SD1.5 + Warli LoRA +\nControlNet scribble,\ncircular padding"),
 ("Previews", "TAESD image at\neach step"),
 ("Vectorize", "two-tone threshold\n+ potrace -> SVG"),
 ("Exports", "tile PNG/SVG, 3x3 repeat,\nwallpapers, tee file,\nflat tee mockup"),
]
W, H = 2000, 760
im = Image.new("RGB", (W, H), "#f5efe3"); d = ImageDraw.Draw(im)
bw, bh, gap, y = 280, 150, 50, 120
x0 = 40
for i, (t, s) in enumerate(boxes):
    x = x0 + i * (bw + gap)
    d.rectangle([x, y, x+bw, y+bh], fill="#c8742f" if i == 2 else "#fffaf0", outline="#2b2b2b", width=3)
    d.text((x+bw/2, y+28), t, font=f(24), fill="#2b2b2b", anchor="mm")
    d.multiline_text((x+bw/2, y+95), s, font=f(16), fill="#2b2b2b", anchor="mm", align="center")
    if i < len(boxes)-1:
        ax = x+bw; d.line([ax+4, y+bh/2, ax+gap-4, y+bh/2], fill="#2b2b2b", width=3)
        d.polygon([(ax+gap-4, y+bh/2), (ax+gap-16, y+bh/2-7), (ax+gap-16, y+bh/2+7)], fill="#2b2b2b")
# composer -> meaning card (placed ids)
cx = x0 + 1*(bw+gap) + bw/2
d.line([cx, y+bh, cx, 420], fill="#2b2b2b", width=3)
d.polygon([(cx, 420), (cx-7, 408), (cx+7, 408)], fill="#2b2b2b")
d.text((cx+10, 300), "placed symbol ids", font=f(16), fill="#2b2b2b")
d.rectangle([cx-135, 420, cx+135, 540], fill="#fffaf0", outline="#2b2b2b", width=3)
d.text((cx, 450), "Meaning card", font=f(22), fill="#2b2b2b", anchor="mm")
d.multiline_text((cx, 500), "lexicon rows + template,\nno LLM", font=f(16), fill="#2b2b2b", anchor="mm", align="center")
# app band
d.rectangle([40, 620, W-40, 710], outline="#2b2b2b", width=2)
d.text((W/2, 665), 'Local FastAPI app: "under the hood" view of every stage, and /study route (annotation, preference survey)', font=f(20), fill="#2b2b2b", anchor="mm")
im.save("architecture.png")
