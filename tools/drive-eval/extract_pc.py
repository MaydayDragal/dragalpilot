# PC wrapper: runs tools/drive-eval/extract.py's per-segment extraction with pclog instead of the device's LogReader
import sys, os, types, glob
TOOLS, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, TOOLS)
import pclog
for n in ("openpilot", "openpilot.tools", "openpilot.tools.lib", "openpilot.tools.lib.logreader"):
    sys.modules[n] = types.ModuleType(n)
sys.modules["openpilot.tools.lib.logreader"].LogReader = pclog.read
import extract
extract.OUT = OUT
for pat in sys.argv[3:]:
    for p in sorted(glob.glob(pat)):
        print(extract.do(p), flush=True)
