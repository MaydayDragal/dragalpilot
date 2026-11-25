"""Renders the comma four driving screen's bottom bar in steering-wheel mode by running the real torque_bar.py
with a stand-in for the drawing library. Usage: render_steer_bar.py <sunnypilot checkout> <out.png>"""
import sys, types, importlib.util, os, tempfile
from PIL import Image, ImageDraw, ImageFont
SP, OUT = sys.argv[1], sys.argv[2]
W, H, SIDE = 536, 240, 60
class C: img = None
def mod(name, **kw):
    m = types.ModuleType(name); m.__dict__.update(kw); sys.modules[name] = m; return m
E = types.SimpleNamespace
def col(c): return (c[0], c[1], c[2], c[3])
def draw_circle(x, y, r, c):
    L = Image.new("RGBA", C.img.size, (0,0,0,0)); ImageDraw.Draw(L).ellipse([x-r, y-r, x+r, y+r], fill=col(c)); C.img = Image.alpha_composite(C.img, L)
mod("pyray", Rectangle=lambda x, y, w, h: E(x=x, y=y, width=w, height=h), Color=lambda r, g, b, a: (r, g, b, a), draw_circle=draw_circle)
def draw_polygon(rect, pts, color=None, gradient=None):
    c = color if color is not None else gradient.colors[-1]
    L = Image.new("RGBA", C.img.size, (0,0,0,0)); ImageDraw.Draw(L).polygon([tuple(p) for p in pts], fill=col(c)); C.img = Image.alpha_composite(C.img, L)
for n in ("opendbc", "openpilot", "openpilot.selfdrive", "openpilot.selfdrive.ui", "openpilot.selfdrive.ui.mici", "openpilot.system", "openpilot.system.ui", "openpilot.system.ui.lib", "openpilot.common"): mod(n)
mod("opendbc.car", ACCELERATION_DUE_TO_GRAVITY=9.81)
def blend(a, b, t): t = min(max(t, 0), 1); return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(4))
mod("openpilot.selfdrive.ui.mici.onroad", blend_colors=blend)
class FOF:
    def __init__(self, x0, rc, dt): self.x = x0; self.a = dt/(rc+dt)
    def update(self, x): self.x = (1-self.a)*self.x + self.a*float(x); return self.x
mod("openpilot.common.filter_simple", FirstOrderFilter=FOF)
mod("openpilot.system.ui.lib.application", gui_app=E(target_fps=60))
mod("openpilot.system.ui.lib.shader_polygon", draw_polygon=draw_polygon, Gradient=lambda **k: E(**k))
class Widget:
    def __init__(self): self._rect = None
    def render(self, rect): self._rect = rect; self._update_state(); self._render(rect)
mod("openpilot.system.ui.widgets", Widget=Widget)
US = E(DISENGAGED=0, LONG_ONLY=1, ENGAGED=2, LAT_ONLY=3)
ui = E(sm={}, status=US.ENGAGED, CP=None)
mod("openpilot.selfdrive.ui.ui_state", ui_state=ui, UIStatus=US)
spec = importlib.util.spec_from_file_location("torque_bar", os.path.join(SP, "openpilot/selfdrive/ui/mici/onroad/torque_bar.py"))
tb = importlib.util.module_from_spec(spec); spec.loader.exec_module(tb)
f = os.path.join(tempfile.gettempdir(), "g70_ui_steer_bar"); open(f, "w").write("2\n")
assert tb.read_steer_bar(f) == (2.0, 8.0) and tb.read_steer_bar(f + "_none") is None
tb.STEER_BAR_FILE = f; orig = tb.read_steer_bar; tb.read_steer_bar = lambda path=f: orig(path)
def backdrop():
    im = Image.new("RGBA", (W, H), (0,0,0,255)); d = ImageDraw.Draw(im); cw = W - SIDE
    for y in range(H):
        v = 26 + int(30*y/H); d.line([(0, y), (cw, y)], fill=(v, v+2, v+6, 255))
    d.polygon([(cw/2-14, 96), (cw/2+14, 96), (cw/2+215, H), (cw/2-215, H)], fill=(52, 55, 60, 255))
    for x0, x1 in ((-11, -140), (11, 140)): d.line([(cw/2+x0, 100), (cw/2+x1, H)], fill=(205,205,205,255), width=3)
    d.rectangle([cw, 0, W, H], fill=(0,0,0,255)); return im
def frame(centre, dev):
    bar = tb.TorqueBar(); rect = E(x=0, y=0, width=W - SIDE, height=H)
    for i in range(900):                       # 15 s: 12 s at the centre angle, then 3 s holding the deviation
        ui.sm["carState"] = E(steeringAngleDeg=centre + (dev if i >= 870 else 0.0))
        C.img = backdrop() if i == 899 else Image.new("RGBA", (W, H), (0,0,0,0)); bar.render(rect)
    return C.img, bar._torque_filter.x
try: font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20); small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 15); big = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
except OSError: font = small = big = ImageFont.load_default()
S = 2; PAD = 28; cases = ((-2.4, 0.0, "wheel steady"), (-2.4, 0.2, "0.2° left: typical highway movement on a calm tune"), (-2.4, -0.6, "0.6° right: ordinary highway correction"), (-2.4, 1.2, "1.2° left: highway hunting (the largest tenth of movement)"), (-2.4, -2.0, "2° right: full bar, common below 45 mph"))
crop = (0, 150, W - SIDE, H); ch = (crop[3]-crop[1])*S
sheet = Image.new("RGB", (PAD*2 + (W-SIDE)*S, 110 + len(cases)*(ch+50)), (245,244,241)); d = ImageDraw.Draw(sheet)
d.text((PAD, 22), "Steering-wheel movement bar (band ±2°)", fill=(11,11,11), font=big)
d.text((PAD, 62), "Bottom of the comma four driving screen, drawn by torque_bar.py. The road is a plain stand-in; the real bar has a soft gradient.", fill=(82,81,78), font=small)
y = 110
for c, dv, label in cases:
    im, x = frame(c, dv); print(label, "bar value %.2f" % x)
    d.text((PAD, y), label, fill=(11,11,11), font=font)
    sheet.paste(im.crop(crop).convert("RGB").resize(((W-SIDE)*S, ch), Image.LANCZOS), (PAD, y+30)); y += ch + 50
sheet.save(OUT); print("saved", sheet.size)
