#!/usr/bin/env python3
"""Assemble the standalone log viewer: one HTML file with everything inlined.

usage: build.py [--layouts DIR] [--out FILE]

Inputs (all in this folder unless given):
  src/index.html, src/app.css, src/*.js   the viewer
  vendor/fzstd.umd.js (+ LICENSE)          zstd decoder (MIT)
  schema.json                              from export_schema.py (pinned cereal schema)
  --layouts                                jotpluggler layouts (default: the sunnypilot checkout's)
Only the Python standard library is needed.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DEFAULT_LAYOUTS = REPO / "sunnypilot" / "openpilot" / "tools" / "jotpluggler" / "layouts"
JS_ORDER = ["bunzip2.js", "logreader.js", "dbc.js", "app.js"]


def json_for_script(obj):
  # no "<" at all inside a <script> element ("</script", "<!--"); the JSON escape < is the same string
  return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c")


def git_rev(path):
  try:
    return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
  except Exception:
    return "unknown"


def fill(template, marker, value):
  parts = template.split(marker)
  if len(parts) != 2:
    raise SystemExit(f"template marker {marker} found {len(parts) - 1} times")
  return parts[0] + value + parts[1]


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--layouts", type=Path, default=DEFAULT_LAYOUTS)
  ap.add_argument("--out", type=Path, default=HERE / "log-viewer.html")
  args = ap.parse_args()

  src = HERE / "src"
  template = (src / "index.html").read_text(encoding="utf-8")
  css = (src / "app.css").read_text(encoding="utf-8")
  license_text = (HERE / "vendor" / "fzstd.LICENSE").read_text(encoding="utf-8").strip()
  js_parts = ["/* fzstd 0.1.1, https://github.com/101arrowz/fzstd\n" + license_text.replace("*/", "* /") + "\n*/",
              (HERE / "vendor" / "fzstd.umd.js").read_text(encoding="utf-8")]
  js_parts += [(src / name).read_text(encoding="utf-8") for name in JS_ORDER]
  js = "\n;\n".join(js_parts)
  if re.search(r"</script", js, re.I) or re.search(r"</style", css, re.I):
    raise SystemExit("inlined code contains a closing script/style tag")

  schema = json.loads((HERE / "schema.json").read_text(encoding="utf-8"))
  layouts = {}
  if args.layouts.is_dir():
    for p in sorted(args.layouts.glob("*.json")):
      layouts[p.name] = json.loads(p.read_text(encoding="utf-8"))
  layouts_src = f"openpilot tools/jotpluggler/layouts @ {git_rev(args.layouts)}" if layouts else "none"
  build = {"schema": schema.get("revision"), "layouts": layouts_src}

  html = template
  html = fill(html, "/*@@CSS@@*/", css)
  html = fill(html, "@@SCHEMA@@", json_for_script(schema))
  html = fill(html, "@@LAYOUTS@@", json_for_script(layouts))
  html = fill(html, "@@BUILD@@", json_for_script(build))
  html = fill(html, "/*@@JS@@*/", js)
  args.out.write_text(html, encoding="utf-8", newline="\n")
  print(f"wrote {args.out} ({len(html.encode('utf-8')) / 1024:.0f} KiB): schema {schema.get('revision')}, {len(layouts)} layouts ({layouts_src})")


if __name__ == "__main__":
  main()
