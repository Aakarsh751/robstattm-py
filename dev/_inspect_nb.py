import json, sys
nb = json.load(open(sys.argv[1], encoding="utf-8"))
print(f"cells: {len(nb['cells'])}")
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] == "code":
        outs = c.get("outputs", [])
        kinds = [o.get("output_type") for o in outs]
        print(f"  cell {i}: outputs={len(outs)} kinds={kinds}")
