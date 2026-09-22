"""Slice logo.stl with CuraEngine using settings that close the top skin."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

CURA_ROOT = Path(r"C:\Program Files\UltiMaker Cura 5.10.0")
ENGINE = CURA_ROOT / "CuraEngine.exe"
FDMPRINTER = CURA_ROOT / "share/cura/resources/definitions/fdmprinter.def.json"
FDMEXTRUDER = CURA_ROOT / "share/cura/resources/definitions/fdmextruder.def.json"

WORKDIR = Path(r"c:\workspaces\some projects\Igorsaha\Printer")
STL_NAME = "logo.stl"
RESOLVED = WORKDIR / "logo_resolved.json"
OUT_GCODE = WORKDIR / "CFFFP_logo_v2.gcode"

START_GCODE = """G28 ; Home all axes
G29 ; Auto bed leveling
G92 E0 ; Reset Extruder
G1 Z2.0 F3000 ; Move Z Axis up
G1 X10.1 Y20 Z0.28 F5000.0 ; Move to start position
G1 X10.1 Y200.0 Z0.28 F1500.0 E15 ; Draw the first line
G1 X10.4 Y200.0 Z0.28 F5000.0 ; Move to side a little
G1 X10.4 Y20 Z0.28 F1500.0 E30 ; Draw the second line
G92 E0 ; Reset Extruder
G1 Z2.0 F3000 ; Move Z Axis up
"""

END_GCODE = """G91 ; Relative positioning
G1 E-2 F2700 ; Retract the filament
G1 Z10 F3000 ; Move Z up 10mm
G90 ; Absolute positioning
G1 X0 Y300 F3000 ; Present print
M104 S0 ; Turn off extruder heating
M140 S0 ; Turn off bed heating
M106 S0 ; Turn off cooling fan
M84 ; Disable steppers
"""


def flatten(node: dict, out: dict) -> None:
    for key, spec in node.items():
        if not isinstance(spec, dict):
            continue
        if "default_value" in spec:
            out[key] = spec["default_value"]
        if "children" in spec:
            flatten(spec["children"], out)


def base_settings() -> dict:
    settings: dict = {}
    for deffile in (FDMPRINTER, FDMEXTRUDER):
        data = json.loads(deffile.read_text(encoding="utf-8"))
        flatten(data.get("settings", {}), settings)
    return settings


OVERRIDES = {
    "machine_width": 360,
    "machine_depth": 360,
    "machine_height": 360,
    "machine_heated_bed": True,
    "machine_extruder_count": 1,
    "extruders_enabled_count": 1,
    "machine_center_is_zero": False,
    "machine_gcode_flavor": "RepRap (Marlin/Sprinter)",
    "machine_start_gcode": START_GCODE,
    "machine_end_gcode": END_GCODE,
    "machine_nozzle_size": 0.4,
    "machine_nozzle_temp_enabled": True,
    "material_diameter": 1.75,
    "material_print_temperature": 210,
    "material_print_temperature_layer_0": 215,
    "material_bed_temperature": 58,
    "material_bed_temperature_layer_0": 60,
    "material_flow": 100,
    "skin_material_flow": 105,
    "infill_material_flow": 100,
    "layer_height": 0.2,
    "layer_height_0": 0.3,
    "line_width": 0.4,
    "wall_line_width": 0.4,
    "skin_line_width": 0.4,
    "infill_line_width": 0.42,
    "adhesion_type": "brim",
    "brim_width": 8,
    "brim_line_count": 10,
    "infill_sparse_density": 30,
    "infill_pattern": "grid",
    "infill_line_distance": 2.8,
    "infill_overlap": 20,
    "infill_wall_line_count": 1,
    "extra_infill_lines_to_support_skins": "walls",
    "zig_zaggify_infill": True,
    "gradual_infill_steps": 0,
    "meshfix_union_all": True,
    "meshfix_keep_open_polygons": True,
    "meshfix_extensive_stitching": True,
    "top_layers": 8,
    "bottom_layers": 5,
    "top_thickness": 1.6,
    "bottom_thickness": 1.0,
    "top_bottom_thickness": 1.6,
    "wall_line_count": 3,
    "wall_thickness": 1.2,
    "skin_overlap": 20,
    "fill_outline_gaps": True,
    "skin_no_small_gaps_heuristic": False,
    "skin_edge_support_layers": 4,
    "skin_edge_support_thickness": 0.8,
    "skin_outline_count": 2,
    "skin_monotonic": True,
    "connect_skin_polygons": True,
    "small_skin_on_surface": True,
    "top_bottom_pattern": "lines",
    "roofing_layer_count": 1,
    "flooring_layer_count": 0,
    "roofing_pattern": "lines",
    "speed_print": 45,
    "speed_infill": 45,
    "speed_wall": 30,
    "speed_wall_0": 25,
    "speed_wall_x": 30,
    "speed_topbottom": 22,
    "speed_roofing": 20,
    "speed_layer_0": 18,
    "speed_travel": 120,
    "speed_travel_layer_0": 80,
    "retraction_enable": True,
    "retraction_amount": 4.5,
    "retraction_speed": 40,
    "retraction_retract_speed": 40,
    "retraction_prime_speed": 30,
    "retraction_extra_prime_amount": 0.04,
    "retraction_combing": "noskin",
    "retraction_min_travel": 1.2,
    "cool_fan_enabled": True,
    "cool_fan_speed": 100,
    "cool_fan_speed_0": 0,
    "cool_fan_full_at_height": 0.6,
    "cool_min_layer_time": 8,
    "ironing_enabled": False,
    "support_enable": False,
    "optimize_wall_printing_order": True,
    "retract_at_layer_change": False,
    "acceleration_enabled": False,
    "jerk_enabled": False,
    "relative_extrusion": False,
    "center_object": False,
    "mesh_position_x": 180,
    "mesh_position_y": 180,
    "mesh_position_z": -4.492,
    "mesh_rotation_matrix": "[[1,0,0], [0,1,0], [0,0,1]]",
    "extruder_nr": 0,
    "infill_angles": "[45, 135]",
    "skin_angles": "[45, 135]",
    "roofing_angles": "[45, 135]",
    "flooring_angles": "[45, 135]",
    "support_infill_angles": "[45, 135]",
    "wall_overhang_speed_factors": "[100]",
}


def _fmt(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, dict)):
        return json.dumps(v)
    return str(v).replace("\n", "\\n")


def main() -> None:
    cmd = [str(ENGINE), "slice", "-v", "-j", str(FDMPRINTER)]
    for key, value in OVERRIDES.items():
        cmd += ["-s", f"{key}={_fmt(value)}"]
    cmd += ["-e0"]
    for key, value in OVERRIDES.items():
        cmd += ["-s", f"{key}={_fmt(value)}"]
    cmd += [
        "-l",
        str(WORKDIR / STL_NAME),
        "-s",
        "mesh_position_x=180",
        "-s",
        "mesh_position_y=180",
        "-s",
        "mesh_position_z=-4.492",
        "-s",
        'mesh_rotation_matrix=[[1,0,0], [0,1,0], [0,0,1]]',
        "-s",
        "extruder_nr=0",
        "-o",
        str(OUT_GCODE),
    ]
    print(f"Command length: {sum(len(x) + 1 for x in cmd)}")
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["CURA_ENGINE_SEARCH_PATH"] = str(CURA_ROOT / "share/cura/resources/definitions")
    if OUT_GCODE.exists():
        OUT_GCODE.write_text("", encoding="utf-8")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKDIR), env=env)
    log = (proc.stdout or "") + "\n" + (proc.stderr or "")
    (WORKDIR / "slice_logo_v2.log").write_text(log, encoding="utf-8", errors="replace")
    print(f"exit={proc.returncode} size={OUT_GCODE.stat().st_size if OUT_GCODE.exists() else 0}")
    if not OUT_GCODE.exists() or OUT_GCODE.stat().st_size < 1000:
        print(log[-3000:])
        raise SystemExit("Slice failed")
    print(f"Wrote {OUT_GCODE} ({OUT_GCODE.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
