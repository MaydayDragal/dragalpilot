"""Renders the comma four (536x240) driving screen with the fan readout by running the real fan_indicator.py and
long_indicator.py widget code with a small stand-in for the drawing library (PIL does the pixels).
Usage: render_fan_ui.py <sunnypilot checkout> <out.png>     (needs Pillow)"""
import sys, types, importlib.util, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SP, OUT = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(SP, "openpilot/selfdrive/assets")
W, H, SIDE = 536, 240, 60

class Tex:
    def __init__(self, im): self.im = im; self.width, self.height = im.size
class Canvas:
    img = None; t = 0.0
def mod(name, **kw):
    m = types.ModuleType(name); m.__dict__.update(kw); sys.modules[name] = m; return m

rl = mod("pyray", Texture=Tex, Font=object, Rectangle=lambda x, y, w, h: types.SimpleNamespace(x=x, y=y, width=w, height=h),
         Vector2=lambda x, y: types.SimpleNamespace(x=x, y=y), Color=lambda r, g, b, a: (r, g, b, a), get_time=lambda: Canvas.t)
def draw_texture_ex(tex, pos, rot, scale, tint):
    im = tex.im.copy(); im.putalpha(im.getchannel("A").point(lambda v: round(v * tint[3] / 255)))
    layer = Image.new("RGBA", Canvas.img.size, (0, 0, 0, 0)); layer.paste(im, (round(pos.x), round(pos.y)), im)
    Canvas.img = Image.alpha_composite(Canvas.img, layer)
_fonts = {}
def pil_font(font, size):
    k = (font, size)
    if k not in _fonts: _fonts[k] = ImageFont.truetype(os.path.join(ASSETS, "fonts", font), size)
    return _fonts[k]
def draw_text_ex(font, text, pos, size, spacing, color):
    # raylib places the top of the line box at pos.y; PIL's "la" anchor places the ascender there: the same to within a pixel
    layer = Image.new("RGBA", Canvas.img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((pos.x, pos.y), text, font=pil_font(font, size), fill=color, anchor="la")
    Canvas.img = Image.alpha_composite(Canvas.img, layer)
rl.draw_texture_ex = draw_texture_ex; rl.draw_text_ex = draw_text_ex
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
    def font(self, weight="Inter-Medium.ttf"): return weight
FW = E(BOLD="Inter-Bold.ttf", SEMI_BOLD="Inter-SemiBold.ttf", MEDIUM="Inter-Medium.ttf", NORMAL="Inter-Medium.ttf")
mod("openpilot.system.ui.lib.application", gui_app=GuiApp(), FontWeight=FW)
def measure_text_cached(font, text, size, spacing=0):
    return E(x=pil_font(font, size).getlength(text), y=size)
mod("openpilot.system.ui.lib.text_measure", measure_text_cached=measure_text_cached)
class Widget:
    def __init__(self): pass
    def render(self, rect): self._render(rect)
mod("openpilot.system.ui.widgets", Widget=Widget)
class SM(dict):
    recv_frame = {"selfdriveState": 10, "deviceState": 10}; alive = {"longitudinalPlan": True}
ui_state = E(sm=SM(), started_frame=0, has_longitudinal_control=True)
mod("openpilot.selfdrive.ui.ui_state", ui_state=ui_state)
spec = importlib.util.spec_from_file_location("g70_long", os.path.join(SP, "openpilot/sunnypilot/selfdrive/controls/lib/g70_long.py"))
g70 = importlib.util.module_from_spec(spec); spec.loader.exec_module(g70)
g70.read_follow_table = lambda *a, **k: (0.75, 1.25, 1.45, 1.75)
g70.GapReader = type("GapReader", (), {"__init__": lambda self, *a, **k: None, "get": lambda self, personality: 0})
sys.modules["openpilot.sunnypilot.selfdrive.controls.lib"].g70_long = g70; sys.modules["openpilot.sunnypilot.selfdrive.controls.lib.g70_long"] = g70
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SP, f"openpilot/selfdrive/ui/mici/onroad/{name}.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
fan_mod = load("fan_indicator"); fan_mod.fan_indicator_enabled = lambda *a, **k: True
fan = fan_mod.FanIndicator(); bars = load("long_indicator").LongIndicator()

def backdrop():
    """a plain stand-in for the road view and the side panel: the real screen shows the camera image here"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 255)); d = ImageDraw.Draw(im); cw = W - SIDE
    for y in range(H):
        v = 26 + int(30 * y / H); d.line([(0, y), (cw, y)], fill=(v, v + 2, v + 6, 255))
    d.polygon([(cw / 2 - 14, 96), (cw / 2 + 14, 96), (cw / 2 + 215, H), (cw / 2 - 215, H)], fill=(52, 55, 60, 255))
    for x0, x1 in ((-11, -140), (11, 140)): d.line([(cw / 2 + x0, 100), (cw / 2 + x1, H)], fill=(205, 205, 205, 255), width=3)
    im = im.filter(ImageFilter.GaussianBlur(0.6)); d = ImageDraw.Draw(im)
    d.rectangle([cw, 0, W, H], fill=(0, 0, 0, 255)); d.ellipse([W - 44, 96, W - 12, 128], fill=(40, 200, 110, 255))   # side panel with the confidence dot
    return im

def frame(percent, alert=False):
    sm = ui_state.sm
    sm["selfdriveState"] = E(enabled=True, alertSize="small" if alert else "none", personality=E(raw=0))
    sm["deviceState"] = E(fanSpeedPercentDesired=percent)
    sm["longitudinalPlan"] = E(hasLead=True, longitudinalPlanSource="lead0"); sm["onroadEvents"] = []
    bars.set_should_draw(True); rect = rl.Rectangle(0, 0, W - SIDE, H)
    for i in range(240):
        Canvas.t += 1 / 60; Canvas.img = backdrop() if i == 239 else Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bars.render(rect); fan.render(rect)
    return Canvas.img

try: font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20); small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 15); big = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
except OSError: font = small = big = ImageFont.load_default()
S, Z = 2, 4; crop = (W - SIDE - 150, 0, W - SIDE, 62); cw, ch = (crop[2] - crop[0]) * Z, (crop[3] - crop[1]) * Z
PAD = 28; rowh = H * S + 64; cases = (30, 60, 100, 0)
sheet = Image.new("RGB", (PAD * 3 + W * S + cw, 110 + len(cases) * rowh + 20), (245, 244, 241)); d = ImageDraw.Draw(sheet)
d.text((PAD, 22), "Fan readout on the driving screen", fill=(11, 11, 11), font=big)
d.text((PAD, 62), "comma four screen, 536 x 240, drawn by fan_indicator.py and long_indicator.py. The road and the side panel are plain stand-ins; text uses the screen's own fonts.", fill=(82, 81, 78), font=small)
y = 110
for pct in cases:
    im = frame(pct)
    d.text((PAD, y), f"Fan setting {pct} %", fill=(11, 11, 11), font=font)
    sheet.paste(im.convert("RGB").resize((W * S, H * S), Image.NEAREST), (PAD, y + 34))
    sheet.paste(im.crop(crop).convert("RGB").resize((cw, ch), Image.NEAREST), (PAD * 2 + W * S, y + 34))
    d.text((PAD * 2 + W * S, y + 34 + ch + 6), f"top right corner, zoom x{Z}", fill=(82, 81, 78), font=small)
    y += rowh
sheet.save(OUT); print("saved", OUT, sheet.size)
