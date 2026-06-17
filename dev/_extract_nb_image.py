"""Extract a PNG output from a notebook cell to a file for inspection."""
import base64, json, sys
nb_path, cell_idx, out_path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
nb = json.load(open(nb_path, encoding="utf-8"))
cell = nb["cells"][cell_idx]
for out in cell.get("outputs", []):
    data = out.get("data", {})
    if "image/png" in data:
        png_b64 = data["image/png"]
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(png_b64))
        print(f"wrote {out_path}")
        break
else:
    print("no image found")
