import matplotlib.pyplot as plt
import matplotlib.patches as patches
import re
import json
import os

def generate_cad_plan(data_json_path, output_image_path):
    """
    Reads the floorplan_data.json and generates a CAD-style Matplotlib plot.
    """
    if not os.path.exists(data_json_path):
        return False

    with open(data_json_path, 'r') as f:
        data = json.load(f)

    # =======================================================================
    # 2. THE SCALING ENGINE
    # =======================================================================
    # Find the absolute min and max pixel coordinates across all template zones
    all_x, all_y = [], []
    for zone in ["boundary", "garage", "front_setback", "rear_setback"]:
        for p in data["template"].get(zone, []):
            all_x.append(p[0])
            all_y.append(p[1])

    if not all_x: # Fallback if no template zones
        all_x, all_y = [0, 256], [0, 256]

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    # Target physical dimensions in feet
    TARGET_WIDTH = 25.0
    TARGET_DEPTH = 45.0

    # Calculate the scale multiplier (feet per pixel)
    # Avoid division by zero
    dx = (max_x - min_x) if (max_x - min_x) != 0 else 256
    dy = (max_y - min_y) if (max_y - min_y) != 0 else 256
    
    scale_x = TARGET_WIDTH / dx
    scale_y = TARGET_DEPTH / dy

    # Helper functions to translate raw pixels to scaled feet
    def tx(x): return (x - min_x) * scale_x
    def ty(y): return (y - min_y) * scale_y

    # =======================================================================
    # 3. ARCHITECTURAL PLOTTING ENGINE
    # =======================================================================
    plt.switch_backend('Agg') # Non-interactive backend for server use
    fig, ax = plt.subplots(figsize=(8, 12), facecolor='#FAFAFA')

    # Styling constants
    COLOR_WALL = '#2C3E50'
    COLOR_ROOM = '#FFFFFF'
    COLOR_SETBACK = '#E8ECEF'
    COLOR_GARAGE = '#FDFEFE'
    DIM_COLOR = '#7F8C8D'

    # Background Drafting Grid (1 ft increments)
    ax.set_facecolor('#FAFAFA')
    for i in range(0, int(max(TARGET_WIDTH, TARGET_DEPTH)) + 10):
        ax.axhline(i, color='#BDC3C7', linewidth=0.5, alpha=0.3)
        ax.axvline(i, color='#BDC3C7', linewidth=0.5, alpha=0.3)

    # Draw Fixed Zones (Setbacks & Garage)
    for zone_key in ["garage", "front_setback", "rear_setback"]:
        pts = data["template"].get(zone_key, [])
        if pts:
            scaled_pts = [(tx(p[0]), ty(p[1])) for p in pts]
            if "setback" in zone_key:
                poly = patches.Polygon(scaled_pts, facecolor=COLOR_SETBACK, edgecolor=COLOR_WALL, 
                                       linewidth=1.5, hatch='///', zorder=2)
                label_text = zone_key.replace('_', '\n').upper()
            else:
                poly = patches.Polygon(scaled_pts, facecolor=COLOR_GARAGE, edgecolor=COLOR_WALL, 
                                       linewidth=1.5, hatch='...', zorder=2)
                label_text = "GARAGE"
            ax.add_patch(poly)
            cx = sum(p[0] for p in scaled_pts) / len(scaled_pts)
            cy = sum(p[1] for p in scaled_pts) / len(scaled_pts)
            bbox_props = dict(boxstyle="square,pad=0.2", fc="white", ec="none", alpha=0.85)
            ax.text(cx, cy, label_text, ha='center', va='center', color=COLOR_WALL, 
                    fontsize=9, fontweight='bold', fontfamily='monospace', bbox=bbox_props, zorder=5)

    # Draw Generated Rooms
    for item in data["rooms"]:
        box = item[0]
        raw_name = item[1][0] if len(item[1]) > 0 else "Room"
        raw_x0, raw_y0, raw_x1, raw_y1 = box
        
        room_name = re.sub(r"(\w)([A-Z])", r"\1\n\2", raw_name).upper() 
        sx0, sy0 = tx(raw_x0), ty(raw_y0)
        sx1, sy1 = tx(raw_x1), ty(raw_y1)
        
        rect = patches.Rectangle((sx0, sy0), sx1-sx0, sy1-sy0, facecolor=COLOR_ROOM, 
                                 edgecolor=COLOR_WALL, linewidth=1.5, zorder=3)
        ax.add_patch(rect)
        
        inner_pad = 0.3 
        inner_rect = patches.Rectangle((sx0+inner_pad, sy0+inner_pad), 
                                       (sx1-sx0)-(inner_pad*2), (sy1-sy0)-(inner_pad*2), 
                                       fill=False, edgecolor=COLOR_WALL, linewidth=0.5, alpha=0.2, zorder=3)
        ax.add_patch(inner_rect)
        
        font_s = 8 if (sx1-sx0) < 6 or (sy1-sy0) < 6 else 10
        ax.text((sx0+sx1)/2, (sy0+sy1)/2, room_name, ha='center', va='center', 
                color=COLOR_WALL, fontsize=font_s, fontfamily='sans-serif', fontweight='medium', zorder=6)

    # Draw Main Property Boundary
    boundary_pts = [(tx(p[0]), ty(p[1])) for p in data["template"]["boundary"]]
    boundary_poly = patches.Polygon(boundary_pts, fill=False, edgecolor=COLOR_WALL, linewidth=3, zorder=7)
    ax.add_patch(boundary_poly)
    
    ax.add_patch(patches.Rectangle((0, 0), TARGET_WIDTH, TARGET_DEPTH, fill=False, 
                                   edgecolor=COLOR_WALL, linestyle='--', linewidth=1.5, zorder=1))

    # =======================================================================
    # 4. ARCHITECTURAL DETAILS
    # =======================================================================
    offset = 2.0
    tick = 0.5
    ax.plot([0, TARGET_WIDTH], [-offset, -offset], color=DIM_COLOR, lw=1)
    ax.plot([-tick, tick], [-offset-tick, -offset+tick], color=DIM_COLOR, lw=1)
    ax.plot([TARGET_WIDTH-tick, TARGET_WIDTH+tick], [-offset-tick, -offset+tick], color=DIM_COLOR, lw=1)
    ax.text(TARGET_WIDTH/2, -offset-0.5, "25'-0\"", ha='center', va='bottom', color=DIM_COLOR, fontsize=10, fontfamily='monospace')

    ax.plot([-offset, -offset], [0, TARGET_DEPTH], color=DIM_COLOR, lw=1)
    ax.plot([-offset-tick, -offset+tick], [-tick, tick], color=DIM_COLOR, lw=1)
    ax.plot([-offset-tick, -offset+tick], [TARGET_DEPTH-tick, TARGET_DEPTH+tick], color=DIM_COLOR, lw=1)
    ax.text(-offset-0.5, TARGET_DEPTH/2, "45'-0\"", ha='right', va='center', rotation=90, color=DIM_COLOR, fontsize=10, fontfamily='monospace')

    plt.figtext(0.85, 0.05, "PROJECT: 5 MARLA GENERATION\nCLIENT: PLANIK AI\nSCALE: 25'x45'\nDRAWN BY: AI", 
                ha="right", va="bottom", fontsize=9, fontfamily='monospace', color=COLOR_WALL,
                bbox=dict(facecolor='white', edgecolor=COLOR_WALL, boxstyle='square,pad=1'))

    ax.invert_yaxis() 
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_xlim(-5, TARGET_WIDTH + 3)
    ax.set_ylim(TARGET_DEPTH + 5, -5)

    plt.tight_layout()
    plt.savefig(output_image_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return True
