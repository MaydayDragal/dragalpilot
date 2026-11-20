"""Renders the comma four (536x240) distance indicator by running the real long_indicator.py widget code with a
small stand-in for the drawing library (PIL does the pixels). Usage: render_gap_ui.py <sunnypilot checkout> <out.png>"""
import sys, types, importlib.util, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SP, OUT = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(SP, "openpilot/selfdrive/assets")
W, H = 536, 240

class Tex:
    def __init__(self, im): self.im = im; self.width, self.height = im.size
class Canvas:
    img = None; t = 0.0
def mod(name, **kw):
    m = types.ModuleType(name); m.__dict__.update(kw); sys.modules[name] = m; return m

# --- stand-ins for the modules the widget imports
rl = mod("pyray", Texture=Tex, Rectangle=lambda x, y, w, h: types.SimpleNamespace(x=x, y=y, width=w, height=h),
         Vector2=lambda x, y: types.SimpleNamespace(x=x, y=y), Color=lambda r, g, b, a: (r, g, b, a), get_time=lambda: Canvas.t)
def draw_texture_ex(tex, pos, rot, scale, tint):
    im = tex.im.copy(); a = im.getchannel("A").point(lambda v: round(v * tint[3] / 255)); im.putalpha(a)
    layer = Image.new("RGBA", Canvas.img.size, (0, 0, 0, 0)); layer.paste(im, (round(pos.x), round(pos.y)), im)
    Canvas.img = Image.alpha_composite(Canvas.img, layer)
rl.draw_texture_ex = draw_texture_ex
class FirstOrderFilter:
    def __init__(self, x0, rc, dt): self.x = x0; self.alpha = dt / (rc + dt)
    def update(self, x): self.x = (1 - self.alpha) * self.x + self.alpha * float(x); return self.x
E = types.SimpleNamespace
log = E(SelfdriveState=E(AlertSize=E(none="none")), OnroadEvent=E(EventName=E(gasPressedOverride="gasPressedOverride")),
        LongitudinalPlan=E(LongitudinalPlanSource=E(e2e="e2e")))
for n in ("openpilot", "openpilot.cereal", "openpilot.common", "openpilot.selfdrive", "openpilot.selfdrive.ui", "openpilot.system", "openpilot.system.ui",
          "openpilot.system.ui.lib", "openpilot.sunnypilot", "openpilot.sunnypilot.selfdrive", "openpilot.sunnypilot.selfdrive.controls", "openpilot.sunnypilot.selfdrive.controls.lib"):
    mod(n)
sys.modules["openpilot.cereal"].log = log
mod("openpilot.common.filter_simple", FirstOrderFilter=FirstOrderFilter)
class GuiApp:
    target_fps = 60
    def texture(self, path, width, height, keep_aspect_ratio=False):
        return Tex(Image.open(os.path.join(ASSETS, path)).convert("RGBA").resize((width, height), Image.BICUBIC))
mod("openpilot.system.ui.lib.application", gui_app=GuiApp())
class Widget:
    def __init__(self): pass
    def render(self, rect): self._render(rect)
mod("openpilot.system.ui.widgets", Widget=Widget)
class SM(dict):
    recv_frame = {"selfdriveState": 10}; alive = {"longitudinalPlan": True}
ui_state = E(sm=SM(), started_frame=0, has_longitudinal_control=True)
mod("openpilot.selfdrive.ui.ui_state", ui_state=ui_state)
spec = importlib.util.spec_from_file_location("g70_long", os.path.join(SP, "openpilot/sunnypilot/selfdrive/controls/lib/g70_long.py"))
g70 = importlib.util.module_from_spec(spec); spec.loader.exec_module(g70)
sys.modules["openpilot.sunnypilot.selfdrive.controls.lib"].g70_long = g70; sys.modules["openpilot.sunnypilot.selfdrive.controls.lib.g70_long"] = g70
GAP = {"v": 0}

def load_widget(four):
    g70.read_follow_table = (lambda *a, **k: (0.75, 1.25, 1.45, 1.75)) if four else (lambda *a, **k: None)
    g70.GapReader = type("GapReader", (), {"__init__": lambda self, *a, **k: None, "get": lambda self, personality: GAP["v"]})
    spec = importlib.util.spec_from_file_location("long_indicator", os.path.join(SP, "openpilot/selfdrive/ui/mici/onroad/long_indicator.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m.LongIndicator()

def backdrop():
    """a plain stand-in for the road view: the real screen shows the camera image here"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 255)); d = ImageDraw.Draw(im)
    for y in range(H):
        v = 26 + int(30 * y / H); d.line([(0, y), (W, y)], fill=(v, v + 2, v + 6, 255))
    d.polygon([(268 - 14, 96), (268 + 14, 96), (268 + 230, H), (268 - 230, H)], fill=(52, 55, 60, 255))
    for x0, x1 in ((-11, -150), (11, 150)): d.line([(268 + x0, 100), (268 + x1, H)], fill=(205, 205, 205, 255), width=3)
    return im.filter(ImageFilter.GaussianBlur(0.6))

def frame(widget, gap, four, seconds, lead=True):
    """run the widget for `seconds` at 60 fps with a change to `gap` at the start, return the last frame"""
    pers = min(gap, 2); GAP["v"] = gap
    sm = ui_state.sm
    sm["selfdriveState"] = E(enabled=True, alertSize="none", personality=E(raw=pers))
    sm["longitudinalPlan"] = E(hasLead=lead, longitudinalPlanSource="lead0"); sm["onroadEvents"] = []
    widget.set_should_draw(True)
    for i in range(int(seconds * 60)):
        Canvas.t += 1 / 60; Canvas.img = backdrop() if i == int(seconds * 60) - 1 else Image.new("RGBA", (W, H), (0, 0, 0, 0))
        widget.render(rl.Rectangle(0, 0, W, H))
    return Canvas.img

def settle(widget, gap, four):
    # arrive from the neighbouring setting so the change highlight is real, then let it finish
    prev = (gap + 1) % (4 if four else 3)
    frame(widget, prev, four, 4.0)
    hi = frame(widget, gap, four, 0.6)       # 0.6 s after the change: highlighted
    st = frame(widget, gap, four, 4.0)       # steady
    return st, hi

try: font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20); small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 15); big = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
except OSError: font = small = big = ImageFont.load_default()
S = 2; Z = 5; crop = (0, 78, 96, 174)          # indicator region for the zoomed view
cw, ch = (crop[2] - crop[0]) * Z, (crop[3] - crop[1]) * Z
PAD = 28; rowh = max(H * S, ch) + 70; colw = W * S + PAD + cw * 2 + PAD * 3
sheet = Image.new("RGB", (PAD + colw, 110 + 4 * rowh + 3 * 20 + 250), (245, 244, 241)); d = ImageDraw.Draw(sheet)
d.text((PAD, 22), "Distance indicator with four gap settings", fill=(11, 11, 11), font=big)
d.text((PAD, 62), "comma four screen, 536 x 240, drawn by the changed long_indicator.py. The road is a plain stand-in for the camera image; the car and bars are the real icons at their real positions.", fill=(82, 81, 78), font=small)
w4 = load_widget(True); y = 110
for gap in range(4):
    st, hi = settle(w4, gap, True)
    d.text((PAD, y), f"Setting {gap + 1}  ({(0.75, 1.25, 1.45, 1.75)[gap]} s)", fill=(11, 11, 11), font=font)
    sheet.paste(st.convert("RGB").resize((W * S, H * S), Image.NEAREST), (PAD, y + 34))
    x2 = PAD + W * S + PAD
    for k, (im, lab) in enumerate(((st, "steady"), (hi, "just after you press the distance button"))):
        z = im.crop(crop).convert("RGB").resize((cw, ch), Image.NEAREST); sheet.paste(z, (x2 + k * (cw + PAD), y + 34))
        d.text((x2 + k * (cw + PAD), y + 34 + ch + 6), f"zoom x{Z}: {lab}", fill=(82, 81, 78), font=small)
    y += rowh + 20
# what the screen shows today for the same four settings
d.text((PAD, y), "For comparison, today's indicator (three bars) on the same four settings", fill=(11, 11, 11), font=font)
w3 = load_widget(False); x = PAD
for gap in range(4):
    st, _ = settle(w3, min(gap, 2), False)
    z = st.crop(crop).convert("RGB").resize(((crop[2] - crop[0]) * 3, (crop[3] - crop[1]) * 3), Image.NEAREST); sheet.paste(z, (x, y + 34))
    d.text((x, y + 34 + z.size[1] + 6), f"setting {gap + 1}", fill=(82, 81, 78), font=small); x += z.size[0] + PAD
sheet.save(OUT); print("saved", OUT, sheet.size)
