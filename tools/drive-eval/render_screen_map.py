"""Every element of the comma four driving screen (536x240) in the situations where they appear together, drawn from
the real icons and fonts at the positions and sizes the widget code uses, with a pixel-level overlap check.

  python render_screen_map.py <sunnypilot checkout> <out.png>      (needs Pillow and numpy)

Positions are transcribed from selfdrive/ui/mici/onroad/*.py and sunnypilot/onroad/blind_spot_indicators.py (file and
line noted per element below). The camera image, the driving path and the lead marker are not drawn: they lie under
all of these. Animated transitions are shown at rest."""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SP, OUT = sys.argv[1], sys.argv[2]
A = os.path.join(SP, "openpilot/selfdrive/assets"); W, H, SIDE, NAV = 536, 240, 60, 261

def tex(path, w, h, flip=False):
    im = Image.open(os.path.join(A, "icons_mici", path)).convert("RGBA").resize((w, h), Image.BICUBIC)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im
def font(name, size): return ImageFont.truetype(os.path.join(A, "fonts", name), size)
def layer(): return Image.new("RGBA", (W, H), (0, 0, 0, 0))
def put(im, x, y, alpha=1.0):
    L = layer(); im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: round(v * alpha))); L.paste(im, (round(x), round(y)), im); return L
def text(s, x, y, fnt, alpha, anchor="la"):
    L = layer(); ImageDraw.Draw(L).text((x, y), s, font=fnt, fill=(255, 255, 255, round(255 * alpha)), anchor=anchor); return L

def elements(cw, gap=3, fan_pct=60, set_speed="77", bsm=False, torque=0.2):
    """name -> layer, for a camera view `cw` px wide"""
    E = {}
    # driver_state.py: 60 px at (16, 10) (augmented_road_view.py set_position)
    L = put(tex("onroad/driver_monitoring/dm_background.png", 60, 60), 16, 10); L = Image.alpha_composite(L, put(tex("onroad/driver_monitoring/dm_person.png", 52, 52), 20, 14, 0.9)); E["driver icon"] = L
    # long_indicator.py: car 35x27 centred (46, 100); four bars (dragalpilot layout)
    L = put(tex("longitudinal/car.png", 35, 27), 46 - 17.5, 100 - 13.5, 0.9)
    for i, ((n, w, h), y) in enumerate(zip((("distance_1", 24, 5), ("distance_1", 32, 7), ("distance_2", 40, 9), ("distance_3", 48, 11)), (120.5, 130.5, 142.5, 156.5))):
        L = Image.alpha_composite(L, put(tex(f"longitudinal/{n}.png", w, h), 46 - w / 2, y - h / 2, 0.9 if i <= gap else 0.35))
    E["lead car and gap bars"] = L
    # hud_renderer.py _draw_steering_wheel: 50 px, centre (21 + 25, H - 14 - 25)
    E["steering wheel"] = put(tex("wheel.png", 50, 50), 21, H - 14 - 50, 0.9)
    # hud_renderer.py TurnIntent: 50x20, centred on the wheel, origin at the top of a box 25 px larger all round
    E["lane change arrow"] = put(tex("turn_intent_left.png", 50, 20), 46 - 25, (H - 14 - 25) - 50, 1.0)
    # torque_bar.py: arc of radius 1200, 14 px thick, 22 px above the bottom, 12.7 degrees wide on a 476 px view
    L = layer(); d = ImageDraw.Draw(L); cx = cw / 2 + 8; cy = H + 1200 - 22; span = 12.7 * min(1.0, cw / 476)
    d.arc([cx - 1214, cy - 1214, cx + 1214, cy + 1214], -90 - span / 2, -90 + span / 2, fill=(255, 255, 255, 64), width=14)
    d.arc([cx - 1214, cy - 1214, cx + 1214, cy + 1214], -90, -90 + span / 2 * torque, fill=(255, 255, 255, 230), width=14); E["torque bar"] = L
    # hud_renderer.py _draw_set_speed: number 112 px at (17, -4), MAX 36 px at (25, 109)
    L = text(set_speed, 17, -4, font("Inter-Bold.ttf", 112), 0.9); E["set speed"] = Image.alpha_composite(L, text("MAX", 25, 109, font("Inter-SemiBold.ttf", 36), 0.9))
    # hud_renderer.py _draw_model_source: 60x44, 10 px from the right, level with the wheel
    E["model icon"] = put(tex("chestnut_green.png", 60, 44), cw - 10 - 60, H - 14 - (50 + 44) / 2)
    # blind_spot_indicators.py: 108x128, 20 px from each edge, 100 px from the top
    E["blind spot left"] = put(tex("onroad/blind_spot_left.png", 108, 128), 20, 100); E["blind spot right"] = put(tex("onroad/blind_spot_left.png", 108, 128, True), cw - 20 - 108, 100)
    # fan_indicator.py: value 36 px bold right-aligned 20 px from the right, 12 px from the top; label 20 px to its left
    fv, fl = font("Inter-Bold.ttf", 36), font("Inter-SemiBold.ttf", 20); val = f"{fan_pct}%"; vw = fv.getlength(val); lw = fl.getlength("FAN")
    L = text(val, cw - 20 - vw, 12, fv, 0.9); E["fan readout"] = Image.alpha_composite(L, text("FAN", cw - 20 - vw - 7 - lw, 12 + (36 - 20) * 0.78, fl, 0.6))
    # alert_renderer.py: small alert is 0.583 of the height, solid then fading
    L = layer(); d = ImageDraw.Draw(L)
    for y in range(140): d.line([(0, y), (cw, y)], fill=(0, 0, 0, 235 if y < 90 else int(235 * (140 - y) / 50)))
    L = Image.alpha_composite(L, text("Changing Lanes", 18, 14, font("Inter-Bold.ttf", 54), 0.95)); E["alert (small)"] = L
    # augmented_road_view.py BookmarkIcon: 180 px, 200 px in from the right edge of the whole screen, centred vertically
    E["bookmark (after a swipe)"] = put(tex("onroad/bookmark_fill.png", 180, 180), W - 200, (H - 180) / 2)
    return E

def backdrop(cw, nav):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 255)); d = ImageDraw.Draw(im)
    for y in range(H):
        v = 26 + int(30 * y / H); d.line([(0, y), (cw, y)], fill=(v, v + 2, v + 6, 255))
    d.polygon([(cw / 2 - 12, 96), (cw / 2 + 12, 96), (cw / 2 + cw * 0.45, H), (cw / 2 - cw * 0.45, H)], fill=(52, 55, 60, 255))
    im = im.filter(ImageFilter.GaussianBlur(0.6)); d = ImageDraw.Draw(im); d.rectangle([cw, 0, W, H], fill=(0, 0, 0, 255))
    if nav:
        d.rounded_rectangle([cw + 8, 8, W - 8, H - 8], 14, fill=(28, 28, 30, 255)); d.text((cw + 24, 96), "navigation\npanel", font=font("Inter-SemiBold.ttf", 26), fill=(150, 150, 150, 255))
    else: d.ellipse([W - 48, 96, W, 144], fill=(40, 200, 110, 255))
    return im

# name, camera width, visible elements, options. Visibility follows the code: the driver icon and the bars hide while the
# set speed shows; the bars, the fan readout and the set speed hide under an alert; the wheel hides on a blind-spot hit.
SCENES = [
    ("1. Cruising, engaged", W - SIDE, ["driver icon", "lead car and gap bars", "steering wheel", "torque bar", "fan readout"], {}),
    ("2. Just after changing the set speed (2.5 s)", W - SIDE, ["set speed", "steering wheel", "torque bar", "fan readout"], {}),
    ("3. Lane change prompt, both blind spots lit, model icon", W - SIDE, ["driver icon", "lead car and gap bars", "lane change arrow", "blind spot left", "blind spot right", "model icon", "torque bar", "fan readout"], {"fan_pct": 100}),
    ("4. Small alert", W - SIDE, ["driver icon", "steering wheel", "torque bar", "alert (small)"], {}),
    ("5. Bookmark swiped in", W - SIDE, ["driver icon", "lead car and gap bars", "steering wheel", "torque bar", "fan readout", "bookmark (after a swipe)"], {}),
    ("6. Navigation panel open, cruising", W - NAV, ["driver icon", "lead car and gap bars", "steering wheel", "torque bar", "fan readout"], {"fan_pct": 100}),
    ("7. Navigation panel open, set speed just changed", W - NAV, ["set speed", "steering wheel", "torque bar"], {}),
]
MINE = ("fan readout", "lead car and gap bars")
def mask(L): return np.array(L.getchannel("A")) > 40
def bbox(m):
    ys, xs = np.where(m); return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1) if len(xs) else None

try: f1 = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 19); f2 = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 14); fb = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
except OSError: f1 = f2 = fb = ImageFont.load_default()
S = 2; PAD = 26; cols = 2; cellw = W * S + PAD; cellh = H * S + 96
rows = math.ceil(len(SCENES) / cols); sheet = Image.new("RGB", (PAD + cols * cellw, 100 + rows * cellh), (245, 244, 241)); d = ImageDraw.Draw(sheet)
d.text((PAD, 20), "Driving screen with every element, per situation", fill=(11, 11, 11), font=fb)
d.text((PAD, 58), "comma four, 536 x 240. Real icons and fonts at the positions in the code; the road is a stand-in. Red outline = two elements share pixels.", fill=(82, 81, 78), font=f2)
print("overlap check (pixels where both elements are visibly drawn):")
for k, (title, cw, names, opt) in enumerate(SCENES):
    E = elements(cw, **opt); im = backdrop(cw, cw < 400); M = {n: mask(E[n]) for n in names}
    for n in names: im = Image.alpha_composite(im, E[n])
    hits = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            both = M[a] & M[b]
            if both.sum(): hits.append((a, b, int(both.sum()), bbox(both)))
    big = im.convert("RGB").resize((W * S, H * S), Image.NEAREST); bd = ImageDraw.Draw(big)
    for a, b, n, bb in hits:
        if "alert" in (a + b) or "bookmark" in (a + b): continue      # these are meant to cover what is under them
        bd.rectangle([bb[0] * S - 3, bb[1] * S - 3, bb[2] * S + 3, bb[3] * S + 3], outline=(230, 60, 60), width=3)
    x = PAD + (k % cols) * cellw; y = 100 + (k // cols) * cellh
    d.text((x, y), title, fill=(11, 11, 11), font=f1); sheet.paste(big, (x, y + 30))
    real = [h for h in hits if "alert" not in (h[0] + h[1]) and "bookmark" not in (h[0] + h[1])]; cover = [h for h in hits if h not in real]
    note = "no overlaps" if not real else "; ".join(f"{a} / {b}: {n} px" for a, b, n, _ in real)
    if cover: note += "   (covers by design: " + ", ".join(sorted({h[0] if ("alert" in h[1] or "bookmark" in h[1]) else h[1] for h in cover})) + ")"
    d.text((x, y + 34 + H * S), note[:150], fill=(190, 40, 40) if real else (82, 81, 78), font=f2)
    print(f"  {title}")
    for a, b, n, bb in hits: print(f"      {a:26s} x {b:26s} {n:5d} px at {bb}" + ("   [new element involved]" if a in MINE or b in MINE else "") + ("   [covering layer]" if (a, b, n, bb) in cover else ""))
    if not hits: print("      none")
    for n in names:
        if n in MINE: print(f"      {n}: occupies {bbox(M[n])}")
sheet.save(OUT); print("saved", OUT, sheet.size)
