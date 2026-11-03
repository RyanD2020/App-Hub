"""Built on Databricks: the platform layers, what each tool uses, and what the platform can do next."""
from views import ui
from views.ui import chip, esc

cfg = ui.cfg()
tools = cfg["tools"]
plat = cfg["platform"]
matrix = plat.get("matrix") or {}

with ui.section("sec-platform"):
    ui.section_head("Built on Databricks", "Every tool here runs on the platform NYL already has",
                    "No new software to buy and no files emailed around. Each layer below is a part of Databricks "
                    "our tools use today.")

    layers = []
    for i, layer in enumerate(plat["layers"], start=1):
        users = "".join(chip(t["short_name"], "plain") for t in tools
                        if (matrix.get(t["id"]) or {}).get(layer["feature"]) == "yes")
        layers.append(f'<div class="layer l{min(i, 4)}"><h3>{esc(layer["title"])}</h3><p>{esc(layer["text"])}</p>'
                      f'<div class="chips">{users}</div></div>')
    ui.html('<div class="stack">' + "".join(layers) + "</div>")

    features = plat["features"]
    rows = []
    for t in tools:
        row = [esc(t["name"])]
        for f in features:
            v = (matrix.get(t["id"]) or {}).get(f)
            row.append('<span class="tick">Yes</span>' if v == "yes" else chip("Planned", "info") if v == "planned" else "")
        rows.append(row)
    note = plat.get("matrix_note") or ""
    ui.html('<div class="table-head"><h3>What each tool uses</h3>'
            f'{chip(note, "review") if note else ""}</div>'
            + ui.html_table_html(["Tool"] + features, rows, center=set(range(1, len(features) + 1))))

with ui.section("sec-platform-next"):
    ui.section_head("What the platform can do next", "Capabilities we haven't used yet",
                    "These are all part of Databricks. Any of them could power the next tool.")
    ui.html('<div class="next-grid">' + "".join(
        f'<div class="card"><div class="eyebrow">{esc(c["eyebrow"])}</div><h3>{esc(c["title"])}</h3>'
        f'<p>{esc(c["text"])}</p></div>' for c in plat["next"]) + "</div>")
