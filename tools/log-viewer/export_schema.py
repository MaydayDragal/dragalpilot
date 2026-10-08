#!/usr/bin/env python3
"""Export the cereal Event schema to a compact JSON the browser log viewer decodes with.

Run with pycapnp against the pinned sunnypilot checkout, e.g. (WSL, checkout venv):
  python export_schema.py <sunnypilot-root> <out.json>

The JSON holds, for every struct reachable from Event, the wire layout (data words, pointer
count, discriminant offset, per-field offset/type/default) and every enum's names by ordinal.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import capnp

NO_DISCRIMINANT = 65535
PRIM = {
  "void": "v", "bool": "b",
  "int8": "i8", "int16": "i16", "int32": "i32", "int64": "i64",
  "uint8": "u8", "uint16": "u16", "uint32": "u32", "uint64": "u64",
  "float32": "f32", "float64": "f64",
  "text": "t", "data": "d", "anyPointer": "a", "interface": "a",
}


class Exporter:
  def __init__(self):
    self.nodes = {}

  @staticmethod
  def node_id(schema):
    return format(int(schema.node.id), "x")

  def type_desc(self, type_proto, schema):
    kind = type_proto.which()
    if kind in PRIM:
      return PRIM[kind]
    if kind == "enum":
      return {"e": self.add_enum(schema)}
    if kind == "struct":
      return {"s": self.add_struct(schema)}
    if kind == "list":
      elem = type_proto.list.elementType
      # elementType raises for primitive elements, so only ask for it when it carries a schema
      elem_schema = schema.elementType if elem.which() in ("enum", "struct", "list") else None
      return {"l": self.type_desc(elem, elem_schema)}
    raise ValueError(f"unhandled type {kind}")

  def add_enum(self, schema):
    nid = self.node_id(schema)
    if nid not in self.nodes:
      names = schema.enumerants
      out = [""] * (max(names.values()) + 1 if names else 0)
      for name, ordinal in names.items():
        out[ordinal] = name
      self.nodes[nid] = {"k": "e", "n": schema.node.displayName.split(":")[-1], "v": out}
    return nid

  @staticmethod
  def default_value(slot):
    dv = slot.defaultValue
    kind = dv.which()
    if kind in ("void", "text", "data", "struct", "list", "anyPointer", "interface"):
      return None
    val = getattr(dv, kind)
    if kind == "bool":
      return 1 if val else None
    if kind == "enum":
      return val or None
    if kind in ("float32", "float64"):
      if math.isnan(val):
        return "NaN"
      if math.isinf(val):
        return "Infinity" if val > 0 else "-Infinity"
      return val if val != 0 or math.copysign(1, val) < 0 else None
    return str(val) if val else None  # 64-bit safe

  def add_struct(self, schema):
    nid = self.node_id(schema)
    if nid in self.nodes:
      return nid
    node = schema.node
    st = node.struct
    entry = {"k": "s", "n": node.displayName.split(":")[-1], "dw": st.dataWordCount, "pc": st.pointerCount,
             "do": st.discriminantOffset if st.discriminantCount else -1, "f": []}
    self.nodes[nid] = entry  # register before recursing (recursive types)
    for name in schema.fieldnames:
      field = schema.fields[name]
      proto = field.proto
      f = {"n": name}
      if proto.discriminantValue != NO_DISCRIMINANT:
        f["d"] = proto.discriminantValue
      if proto.which() == "group":
        f["g"] = self.add_struct(field.schema)
      else:
        slot = proto.slot
        kind = slot.type.which()
        needs_schema = kind in ("enum", "struct", "list")
        f["t"] = self.type_desc(slot.type, field.schema if needs_schema else None)
        f["o"] = slot.offset
        dv = self.default_value(slot)
        if dv is not None:
          f["dv"] = dv
      entry["f"].append(f)
    return nid


def main():
  if len(sys.argv) != 3:
    print(f"usage: {sys.argv[0]} <sunnypilot-root> <out.json>", file=sys.stderr)
    sys.exit(2)
  root = Path(sys.argv[1]).resolve()
  capnp.remove_import_hook()
  log = capnp.load(str(root / "openpilot" / "cereal" / "log.capnp"), imports=[str(root / "opendbc_repo" / "opendbc" / "car")])
  ex = Exporter()
  event_id = ex.add_struct(log.Event.schema)
  try:
    sha = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
  except Exception:
    sha = "unknown"
  out = {"source": "sunnypilot openpilot/cereal/log.capnp", "revision": sha, "root": event_id, "nodes": ex.nodes}
  Path(sys.argv[2]).write_text(json.dumps(out, separators=(",", ":")))
  print(f"{len(ex.nodes)} nodes, revision {sha}")


if __name__ == "__main__":
  main()
