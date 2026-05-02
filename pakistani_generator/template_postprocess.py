"""
template_postprocess.py
========================
After Graph2Plan generates a floor plan inside a known boundary, this module
composites the generated rooms together with pre-defined "fixed zones"
(garage, front setback, rear setback) and the original boundary outline.

DRAWING ORDER (back → front):
  1. White background
  2. Fixed template zones (garage / setbacks)  ← painted first so rooms sit on top
  3. Generated rooms from Graph2Plan
  4. Room labels (labelled image only)
  5. Zone labels (labelled image only)
  6. Boundary outline (always last, so it is never buried)

HOW TO ADD A NEW TEMPLATE:
  - Open the boundary PNG in an image editor at 256×256
  - Identify where the garage, front setback, and rear setback should sit
  - Add a new elif branch in _template_for() with the pixel coordinates
  - Zone coordinates are (x, y) tuples defining a polygon in 256×256 space
"""

import os
import json
import hashlib
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# Room fill colours (matching Graph2Plan's palette)
# ---------------------------------------------------------------------------
ROOM_COLORS = {
    "LivingRoom":  (245, 242, 229),
    "MasterRoom":  (253, 244, 171),
    "SecondRoom":  (253, 244, 171),
    "GuestRoom":   (253, 244, 171),
    "ChildRoom":   (253, 244, 171),
    "StudyRoom":   (253, 244, 171),
    "Kitchen":     (234, 216, 214),
    "Bathroom":    (205, 233, 252),
    "Balcony":     (208, 216, 135),
    "DiningRoom":  (244, 242, 229),
    "Entrance":    (244, 242, 229),
    "Storage":     (249, 222, 189),
}

# Fixed zone colours with hatching support
ZONE_STYLE = {
    "boundary":      {"fill": (255, 255, 255), "outline": (0, 0, 0), "hatch": None, "label": ""},
    "garage":        {"fill": (245, 250, 255), "outline": None, "hatch": (0, 110, 200), "label": "Garage"},
    "front_setback": {"fill": (255, 253, 245), "outline": None, "hatch": (200, 40, 40), "label": "Front\nSetback"},
    "rear_setback":  {"fill": (255, 253, 245), "outline": None, "hatch": (200, 40, 40), "label": "Rear\nSetback"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stable_color(name: str) -> Tuple[int, int, int]:
    """Deterministic pastel colour for unknown room types."""
    d = hashlib.md5(name.encode()).digest()
    return 150 + d[0] % 90, 150 + d[1] % 90, 150 + d[2] % 90


def _draw_zone(draw: ImageDraw.Draw, line_draw: ImageDraw.Draw, pts: List[Tuple[int, int]],
               style: dict, label: bool = False, canvas_size: Tuple[int, int] = (256, 256)) -> None:
    """Draw a zone with diagonal hatching and an outline (via line_mask)."""
    from PIL import ImageChops
    
    # 1. Draw light solid background
    draw.polygon(pts, fill=style["fill"])

    # 2. Draw diagonal hatching using combined masks
    if style.get("hatch"):
        poly_mask = Image.new("L", canvas_size, 0)
        ImageDraw.Draw(poly_mask).polygon(pts, fill=255)
        
        line_mask_h = Image.new("L", canvas_size, 0)
        lm_draw = ImageDraw.Draw(line_mask_h)
        spacing = 8
        for i in range(-canvas_size[0], canvas_size[0] + canvas_size[1], spacing):
            lm_draw.line([(i, 0), (i + canvas_size[1], canvas_size[1])], fill=255, width=1)
            
        combined_mask = ImageChops.multiply(poly_mask, line_mask_h)
        hatch_color_img = Image.new("RGB", canvas_size, style["hatch"])
        draw._image.paste(hatch_color_img, (0, 0), combined_mask)

    # 3. Draw outline into the master line_draw
    if style.get("outline"):
        line_draw.polygon(pts, outline=255, width=2)

    if label:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        cx = (min(xs) + max(xs)) // 2
        cy = (min(ys) + max(ys)) // 2
        lines = style["label"].split("\n")
        for i, line in enumerate(lines):
            offset = (i - (len(lines) - 1) / 2) * 9
            draw.text(
                (cx, cy + offset),
                line,
                fill=style["outline"],
                anchor="mm",
            )


def _read_cookie_boundary(boundary_id: str) -> Optional[List[List[float]]]:
    """Load the boundary polygon from the Graph2Plan dataset."""
    from Houseweb import views as vw
    vw.ensure_initialized()
    name = boundary_id.split(".")[0]
    if name not in vw.testNameList:
        return None
    idx = vw.testNameList.index(name)
    data = vw.test_data[idx]
    boundary = data.boundary[:, :2].tolist()
    return [[float(p[0]), float(p[1])] for p in boundary]


# ---------------------------------------------------------------------------
# Template definitions  (256 × 256 pixel space)
# ---------------------------------------------------------------------------

def _template_for(boundary_name: str) -> Optional[dict]:
    """
    Return the fixed-zone polygon definitions for a given boundary ID,
    or None if no template exists yet.
    """
    name = boundary_name.split(".")[0]

    # ------------------------------------------------------------------
    # Boundary 850
    # ------------------------------------------------------------------
    if name == "850":
        return {
            "boundary": [
                (93, 103), (107, 103), (110, 103), (110, 66),
                (196, 66), (196, 191), (151, 191), (151, 177),
                (109, 177), (109, 191), (61, 191), (61, 103),
            ],
            "garage": [
                (61, 45), (109, 45),
                (109, 103), (61, 103),
            ],
            "front_setback": [
                (109, 46), (196, 46),
                (196, 66), (109, 66),
            ],
            "rear_setback": [
                (110, 177), (151, 177),
                (151, 191), (110, 191),
            ],
            "side_setback": [],
        }

    return None


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_template_result(boundary_id: str, roomret: List, output_dir: str) -> bool:
    """
    Composite the Graph2Plan output with the matching template zones and
    save PNG, SVG, and JSON data files.
    """
    template = _template_for(boundary_id)
    boundary_pts = _read_cookie_boundary(boundary_id)
    
    if boundary_pts is None:
        return False  # boundary not found in dataset

    # If no custom template exists, create a default one with just the boundary
    if template is None:
        template = {
            "boundary": [tuple(p) for p in boundary_pts],
            "garage": [],
            "front_setback": [],
            "rear_setback": [],
            "side_setback": []
        }

    os.makedirs(output_dir, exist_ok=True)

    SIZE = (256, 256)
    labelled = Image.new("RGB", SIZE, "white")
    clean    = Image.new("RGB", SIZE, "white")
    dl = ImageDraw.Draw(labelled)
    dc = ImageDraw.Draw(clean)

    # STEP 0 — Create master line masks and room ID map
    line_mask_l = Image.new("L", SIZE, 0)
    line_mask_c = Image.new("L", SIZE, 0)
    ll = ImageDraw.Draw(line_mask_l)
    lc = ImageDraw.Draw(line_mask_c)
    
    room_id_map = Image.new("I", SIZE, 0)
    rm_draw = ImageDraw.Draw(room_id_map)

    # STEP 1 — Template Zones
    zone_order = ["boundary", "garage", "front_setback", "rear_setback"]
    zone_to_id = {"boundary": 1001, "garage": 1002, "front_setback": 1003, "rear_setback": 1004}
    
    for zone_key in zone_order:
        if zone_key not in template or not template[zone_key]:
            continue
        pts = [tuple(p) for p in template[zone_key]]
        style = ZONE_STYLE[zone_key]
        _draw_zone(dl, ll, pts, style, label=False)
        _draw_zone(dc, lc, pts, style, label=False)
        rm_draw.polygon(pts, fill=zone_to_id[zone_key])

    # STEP 2 — Rooms
    room_types = list(set([item[1][0] if len(item) > 1 and item[1] else "Room" for item in roomret]))
    type_to_id = {name: (i + 1) for i, name in enumerate(room_types)}

    for item in roomret:
        box       = item[0]
        room_name = item[1][0] if len(item) > 1 and item[1] else "Room"
        x0, y0, x1, y1 = [int(round(v)) for v in box]
        color = ROOM_COLORS.get(room_name, _stable_color(room_name))
        dl.rectangle([x0, y0, x1, y1], fill=color)
        dc.rectangle([x0, y0, x1, y1], fill=color)
        rm_draw.rectangle([x0, y0, x1, y1], fill=type_to_id[room_name])

    # STEP 3 — Edge Detection (Merge rooms)
    pixels = room_id_map.load()
    for y in range(SIZE[1]-1):
        for x in range(SIZE[0]-1):
            curr = pixels[x, y]
            if curr != pixels[x+1, y]:
                ll.line([(x+1, y), (x+1, y+1)], fill=255, width=2)
                lc.line([(x+1, y), (x+1, y+1)], fill=255, width=2)
            if curr != pixels[x, y+1]:
                ll.line([(x, y+1), (x+1, y+1)], fill=255, width=2)
                lc.line([(x, y+1), (x+1, y+1)], fill=255, width=2)

    # STEP 4 — Apply Masks
    black_img = Image.new("RGB", SIZE, (0, 0, 0))
    labelled.paste(black_img, (0, 0), line_mask_l)
    clean.paste(black_img, (0, 0), line_mask_c)

    # STEP 5 — Smart Labels
    room_groups = {}
    for item in roomret:
        box       = item[0]
        room_name = item[1][0] if len(item) > 1 and item[1] else "Room"
        if room_name not in room_groups: room_groups[room_name] = []
        room_groups[room_name].append(box)

    for room_name, boxes in room_groups.items():
        min_x = min(b[0] for b in boxes)
        min_y = min(b[1] for b in boxes)
        max_x = max(b[2] for b in boxes)
        max_y = max(b[3] for b in boxes)
        cx, cy = (min_x + max_x) // 2, (min_y + max_y) // 2
        d_name = "".join([" " + c if c.isupper() and i > 0 else c for i, c in enumerate(room_name)]).strip()
        dl.text((cx, cy), d_name, fill=(0, 0, 0), anchor="mm")

    for zone_key in zone_order:
        if zone_key not in template or not template[zone_key]: continue
        pts = template[zone_key]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        cx, cy = (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2
        lines = ZONE_STYLE[zone_key]["label"].split("\n")
        for i, line in enumerate(lines):
            offset = int((i - (len(lines) - 1) / 2) * 9)
            dl.text((cx, cy + offset), line, fill=(0, 0, 0), anchor="mm")

    # STEP 6 — Boundary Outline
    poly = [tuple(p) for p in boundary_pts]
    ImageDraw.Draw(labelled).polygon(poly, outline=(0, 0, 0), width=2)
    ImageDraw.Draw(clean).polygon(poly, outline=(0, 0, 0), width=2)

    # STEP 7 — Auto-crop
    def auto_crop(img, padding=10):
        from PIL import ImageOps
        inverted = ImageOps.invert(img.convert("RGB"))
        bbox = inverted.getbbox()
        if bbox:
            l, t, r, b = bbox
            return img.crop((max(0, l-padding), max(0, t-padding), min(img.width, r+padding), min(img.height, b+padding)))
        return img

    final_labelled = auto_crop(labelled)
    final_clean    = auto_crop(clean)

    # Save outputs
    final_labelled.save(os.path.join(output_dir, "final_labelled.png"))
    final_clean.save(os.path.join(output_dir, "final_unlabelled.png"))
    
    with open(os.path.join(output_dir, "floorplan_data.json"), "w") as f:
        json.dump({"rooms": roomret, "template": template}, f, indent=2)

    # Save professional SVG version
    _save_svg(os.path.join(output_dir, "floorplan.svg"), template, roomret)

    # Save final CAD-style drafting output
    try:
        from pakistani_generator.cad_renderer import generate_cad_plan
        generate_cad_plan(os.path.join(output_dir, "floorplan_data.json"), 
                          os.path.join(output_dir, "final_cad.png"))
    except Exception as e:
        print(f"CAD Rendering Error: {e}")

    return True


def _save_svg(filepath: str, template: dict, roomret: List) -> None:
    """Generate a clean architectural SVG with vector patterns."""
    svg_header = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<svg width="256" height="256" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">\n'
        '  <defs>\n'
        '    <pattern id="hatch-blue" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">\n'
        '      <line x1="0" y1="0" x2="0" y2="6" stroke="#006ec8" stroke-width="0.5" />\n'
        '    </pattern>\n'
        '    <pattern id="hatch-red" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">\n'
        '      <line x1="0" y1="0" x2="0" y2="6" stroke="#c82828" stroke-width="0.5" />\n'
        '    </pattern>\n'
        '  </defs>\n'
        '  <rect width="256" height="256" fill="white" />\n'
    )
    
    with open(filepath, "w") as f:
        f.write(svg_header)
        zone_order = ["boundary", "garage", "front_setback", "rear_setback"]
        for zk in zone_order:
            if zk not in template or not template[zk]: continue
            pts = " ".join([f"{p[0]},{p[1]}" for p in template[zk]])
            fill = "none"
            if zk == "garage": fill = "url(#hatch-blue)"
            elif "setback" in zk: fill = "url(#hatch-red)"
            f.write(f'  <polygon points="{pts}" fill="{fill}" stroke="black" stroke-width="1" />\n')

        for item in roomret:
            box = item[0]
            name = item[1][0] if len(item) > 1 and item[1] else "Room"
            x0, y0, x1, y1 = [int(round(v)) for v in box]
            c = ROOM_COLORS.get(name, (200, 200, 200))
            f_hex = '#%02x%02x%02x' % c
            f.write(f'  <rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="{f_hex}" stroke="black" stroke-width="1" />\n')
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            d_name = "".join([" " + c if c.isupper() and i > 0 else c for i, c in enumerate(name)]).strip()
            f.write(f'  <text x="{cx}" y="{cy}" font-family="sans-serif" font-size="8" text-anchor="middle" dominant-baseline="middle" fill="black">{d_name}</text>\n')

        f.write('</svg>')