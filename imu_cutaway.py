"""Standalone isometric SVG cutaway of a capacitive MEMS accelerometer.

Displacement is deliberately exaggerated for legibility; the rendered proof
mass motion is clamped to a fraction of the comb gap so moving and fixed teeth
never cross. Figure dimensions are illustrative, not package scale.
"""

from collections.abc import Sequence
from html import escape

WIDTH, HEIGHT = 960, 620
STAGES = {"Pattern", "Release", "Package", "Readout"}
MAX_SHIFT = 2.0
INPUT_GAIN = MAX_SHIFT / 0.8


def cutaway(displacement_um: float, stage: str) -> str:
    """Return a detailed light-theme isometric SVG cutaway.

    ``displacement_um`` is a signed, intentionally exaggerated teaching input.
    Its visual effect is bounded so rotor and stator fingers remain separated.
    ``stage`` must be Pattern, Release, Package or Readout.
    """
    stage = stage if stage in STAGES else "Release"
    xshift = max(-MAX_SHIFT, min(MAX_SHIFT, float(displacement_um) * INPUT_GAIN))
    active = {"Pattern": 0, "Release": 1, "Package": 2, "Readout": 3}[stage]
    parts = []

    def path(
        d: str,
        fill: str = "none",
        stroke: str = "#66717b",
        sw: float = 1,
        extra: str = "",
    ) -> None:
        parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-linejoin="round" stroke-linecap="round" {extra}/>'
        )

    def poly(
        points: Sequence[tuple[float, float]],
        fill: str,
        stroke: str = "#59656f",
        sw: float = 1,
    ) -> None:
        path("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points) + " Z", fill, stroke, sw)

    def line(
        points: Sequence[tuple[float, float]],
        stroke: str = "#68737d",
        sw: float = 1,
        dash: str = "",
    ) -> None:
        path(
            "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points),
            "none",
            stroke,
            sw,
            f'stroke-dasharray="{dash}"' if dash else "",
        )

    def dot(x: float, y: float, r: float = 2.0, fill: str = "#68737d") -> None:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>')

    # Axonometric projection: plan axes project down-left/down-right; z rises.
    def P(x: float, y: float, z: float) -> tuple[float, float]:
        return (480 + (x - y) * 1.15, 348 + (x + y) * 0.57 - z * 1.45)

    def prism(
        x: float,
        y: float,
        w: float,
        d: float,
        z: float,
        h: float,
        top: str,
        side: str = "#c1c9cf",
        front: str = "#aab4bc",
        outline: str = "#64717a",
    ) -> list[tuple[float, float]]:
        q = [P(x, y, z), P(x + w, y, z), P(x + w, y + d, z), P(x, y + d, z)]
        qt = [P(x, y, z + h), P(x + w, y, z + h), P(x + w, y + d, z + h), P(x, y + d, z + h)]
        poly([q[0], q[1], qt[1], qt[0]], side, outline)
        poly([q[1], q[2], qt[2], qt[1]], front, outline)
        poly(qt, top, outline)
        return qt

    def toprect(
        x: float,
        y: float,
        w: float,
        d: float,
        z: float,
        fill: str,
        stroke: str = "#65717a",
        sw: float = 0.8,
    ) -> None:
        poly([P(x, y, z), P(x + w, y, z), P(x + w, y + d, z), P(x, y + d, z)], fill, stroke, sw)

    # Paper field, soft contact shadow and package support feet.
    parts.append('<rect width="960" height="620" fill="#f8fafb"/>')
    parts.append('<ellipse cx="480" cy="456" rx="338" ry="88" fill="#34495a" opacity=".08"/>')
    for x, y in [(-132, -67), (132, -67), (132, 67), (-132, 67)]:
        prism(x - 8, y - 7, 16, 14, 0, 8, "#dce2e6", "#b5bec5", "#aab4bc")
        toprect(x - 5, y - 4, 10, 8, 8, "#f4f6f7")

    # Ceramic package base/deck, rim and inset die cavity.
    prism(-150, -88, 300, 176, 8, 22, "#edf1f3", "#c9d1d6", "#b8c2c9")
    toprect(-141, -79, 282, 158, 30, "#e2e8eb")
    toprect(-132, -70, 264, 140, 31, "#d4dde2", "#8c9aa4", 1)
    # Four deck ledges, tiny fasteners and ceramic seam details.
    for x in [-128, 128]:
        for y in [-65, 65]:
            dot(*P(x, y, 31), 2.2, "#78858e")
            dot(*P(x, y, 31.2), 0.8, "#f5f7f8")
    for y in [-73, 73]:
        line([P(-133, y, 31), P(133, y, 31)], "#a3afb7", 0.7)
    for x in [-137, 137]:
        line([P(x, -68, 31), P(x, 68, 31)], "#a3afb7", 0.7)

    # Bond pads at the edge of the exposed die and fine gold wire bonds.
    for i in range(6):
        x = -88 + i * 35
        toprect(x, -65, 12, 8, 32, "#c79b58", "#8b7046", 0.65)
        toprect(x, 57, 12, 8, 32, "#c79b58", "#8b7046", 0.65)
    # Silicon die: beveled-looking body with dark sidewalls and a pale top.
    prism(-108, -53, 216, 106, 32, 8, "#dce9ed", "#95a8b1", "#82969f")
    toprect(-101, -46, 202, 92, 40, "#e9f0f2", "#9baab1", 0.9)
    # Edge seal strips and die corner fiducials.
    for y in [-44, 43]:
        toprect(-99, y, 198, 1.5, 40.2, "#becbd0", "none", 0)
    for x in [-96, 96]:
        for y in [-41, 41]:
            toprect(x - 2, y - 2, 4, 4, 40.3, "#84959d", "#64747c", 0.5)
            dot(*P(x, y, 40.5), 0.8, "#f6f8f9")

    # Silicon substrate pockets and oxide-colored isolation rails.
    for x in [-82, 82]:
        toprect(x - 4, -30, 8, 60, 40.4, "#cfdde1", "#a5b5bc", 0.5)
    for y in [-33, 33]:
        toprect(-83, y - 1.4, 166, 2.8, 40.45, "#d5e0e4", "#aab9bf", 0.5)
    # Etched cavity floor, visible darkened to make released structure legible.
    toprect(-66, -25, 132, 50, 40.5, "#c3d1d6", "#9cadb4", 0.6)
    toprect(-58, -20, 116, 40, 40.6, "#b8c8ce", "#94a6ad", 0.5)

    # Suspension anchors and their collars sit on the cavity floor.
    anchor_xy = [(-53, -21), (-53, 21), (53, -21), (53, 21)]
    for x, y in anchor_xy:
        toprect(x - 5, y - 4, 10, 8, 40.8, "#8798a0", "#5d6e77", 0.7)
        toprect(x - 3.1, y - 2.5, 6.2, 5, 41.8, "#dce4e7", "#71828b", 0.65)
        dot(*P(x, y, 42), 1.1, "#53636c")
        # Anchor slots indicate the fixed silicon beneath the flexures.
        toprect(x - 1.4, y - 1, 2.8, 2, 42.1, "#677983", "none", 0)

    # Fixed comb banks, mounted on the substrate; each tooth is a solid beam.
    fixed_rows = [-40, 40]
    for row in fixed_rows:
        toprect(-47, row - 3, 94, 6, 42.1, "#899aa2", "#5e7079", 0.65)
        toprect(-43, row - 1.6, 86, 3.2, 43, "#c5d2d7", "#687982", 0.6)
        # tooth positions alternate along x; x-directed acceleration shifts mass.
        for i in range(9):
            tooth_x = -37 + i * 9.2
            toprect(tooth_x, row - 8, 2.2, 10, 43, "#d8e2e5", "#73848c", 0.55)
            toprect(tooth_x, row - 2, 2.2, 10, 43, "#d8e2e5", "#73848c", 0.55)
            # etched tooth-tip highlights create thin visible capacitive gaps.
            line(
                [P(tooth_x + 0.25, row - 7.5, 43.2), P(tooth_x + 0.25, row - 1, 43.2)],
                "#f9fbfc",
                0.55,
            )

    # Four pairs of long folded flexures bridge mounted anchors to moving mass.
    spring_groups = []
    for sign in [-1, 1]:
        y = sign * 16
        for x0, x1 in [(-53, -34), (34, 53)]:
            pts = []
            for j in range(9):
                xx = x0 + (x1 - x0) * j / 8
                yy = y + (2.0 if j % 2 else -2.0)
                pts.append(P(xx, yy, 45))
            line(pts, "#607681", 1.7)
            line([(a, b - 1.0) for a, b in pts], "#eef4f6", 0.65)
            spring_groups.append(pts)
    # Movable proof mass and rotor combs are grouped at the same x translation.
    parts.append(f'<g transform="translate({xshift:.2f} 0)" data-moving="proof-mass">')
    prism(-33, -17, 66, 34, 43.2, 4.3, "#bacbd1", "#82969f", "#748992")
    toprect(-27, -12, 54, 24, 47.5, "#d5e2e6", "#81939b", 0.7)
    # Rotor fingers extend from mass into fixed fingers without crossing at bounds.
    for i in range(9):
        finger_x = -32.5 + i * 9.2
        toprect(finger_x, -31, 2.0, 17, 46.2, "#aabdc4", "#6c8089", 0.5)
        toprect(finger_x, 14, 2.0, 17, 46.2, "#aabdc4", "#6c8089", 0.5)
        line([P(finger_x + 0.25, -29, 46.4), P(finger_x + 0.25, -15, 46.4)], "#eef4f6", 0.55)
    # Trim bars and etched mass ribs emphasize the substantial suspended body.
    for i in range(7):
        rib_x = -23 + i * 7.5
        toprect(rib_x, -9, 1.2, 18, 47.7, "#a9bbc2", "#81949c", 0.35)
    for x in [-29, 29]:
        toprect(x - 1, -14, 2, 28, 47.8, "#879ba4", "#687b84", 0.45)
    # Mass contact stops leave a clear overtravel buffer at either side.
    for x in [-37, 37]:
        toprect(x - 1.4, -4, 2.8, 8, 44.8, "#d5aa66", "#94774c", 0.5)
        dot(*P(x, 0, 45), 0.8, "#fff8ea")
    parts.append("</g>")

    # Readout differential capacitance routing, grounded guards and via dots.
    for i in range(5):
        x = -28 + i * 14
        line([P(x, -31, 43.1), P(x, -47, 43.1)], "#768992", 0.8)
        line([P(x, 31, 43.1), P(x, 47, 43.1)], "#768992", 0.8)
        dot(*P(x, -47, 43.2), 1.2, "#59707a")
    # Thin differential sense traces connect the comb buses to bond pads.
    for i in range(4):
        x = -24 + i * 16
        line([P(x, -46, 40.8), P(x, -53, 40.8), P(-80 + i * 25, -61, 40.8)], "#c18c47", 0.9)
        line([P(x, 46, 40.8), P(x, 53, 40.8), P(-80 + i * 25, 61, 40.8)], "#c18c47", 0.9)
    # Header pins exit the package sides; each has a heel, neck and plated tip.
    for side in [-1, 1]:
        for i in range(8):
            y = -59 + i * 17
            x = side * 150
            toprect(x - 3, y - 4, 6, 8, 19, "#b58b4f", "#806b49", 0.5)
            # projection of outward pin as a narrow metal strip seated on deck
            toprect((140 if side > 0 else -164), y - 2, 24, 4, 16, "#d4b575", "#8a734e", 0.6)
            line([P(side * 143, y, 20), P(side * 160, y, 18)], "#f5e7c7", 0.8)
    # Bond wires are arcs from die pad to package shelf; no external dependencies.
    for i in range(6):
        x = -82 + i * 33
        for ysign in [-1, 1]:
            y = ysign * 61
            sx, sy = P(x, y, 40.7)
            ex, ey = P(x + 4, ysign * 70, 31.5)
            cx = (sx + ex) / 2
            cy = min(sy, ey) - 11
            path(f"M{sx:.1f},{sy:.1f} Q{cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}", "none", "#a67c3c", 1.1)
            path(
                f"M{sx:.1f},{sy - 1:.1f} Q{cx:.1f},{cy - 1:.1f} {ex:.1f},{ey - 1:.1f}",
                "none",
                "#eed8a4",
                0.55,
            )
    # Removable package lid (visible as a raised rear cap in the Package stage).
    if active >= 2:
        prism(-146, -86, 292, 18, 52, 17, "#eaf0f3", "#c5d0d6", "#b5c1c8")
        toprect(-139, -82, 278, 10, 69, "#f8fafb", "#c0cbd1", 0.65)
        for x in [-130, 130]:
            dot(*P(x, -77, 69), 1.5, "#829099")
    # Readout path glows only in the Readout stage; geometry remains identical.
    if active == 3:
        for i in range(4):
            x = -24 + i * 16
            line([P(x, -46, 43.3), P(x, -53, 43.3), P(-80 + i * 25, -61, 43.3)], "#1786a0", 1.6)
            line([P(x, 46, 43.3), P(x, 53, 43.3), P(-80 + i * 25, 61, 43.3)], "#1786a0", 1.6)
        # Differential capacitance bars on the corner instrument plate.
        parts.append('<g opacity=".98">')
        parts.append(
            '<rect x="744" y="123" width="170" height="112" rx="12" '
            'fill="#ffffff" stroke="#c8d2d8"/>'
        )
        parts.append(
            '<text x="762" y="149" font-family="system-ui,sans-serif" font-size="11" '
            'letter-spacing="1.4" fill="#697780">DIFFERENTIAL C</text>'
        )
        for i, h in enumerate([26, 39, 52, 64, 73, 58, 45]):
            parts.append(
                f'<rect x="766" y="{207 - h}" width="9" height="{h}" rx="2" '
                f'fill="#5d9cab" opacity="{0.48 + i * 0.055:.2f}"/>'
            )
        parts.append('<path d="M758 207 H898" stroke="#c2cdd2" stroke-width="1"/>')
        parts.append("</g>")
    # Exploded-process cue for Pattern/Release; released die region stays same.
    if active == 0:
        for x in [-84, -42, 0, 42, 84]:
            line([P(x, -49, 41), P(x, -49, 44)], "#8299a3", 0.7, "2 2")
    elif active == 1:
        # Open etched wells are picked out with a turquoise rim, not a floating label.
        for y in [-25, 25]:
            line([P(-66, y, 40.8), P(66, y, 40.8)], "#4d9caf", 1.0)

    # Compact process-stage rail and calibrated displacement scale.
    labels = ["Pattern", "Release", "Package", "Readout"]
    parts.append('<g font-family="system-ui,-apple-system,sans-serif">')
    parts.append(
        '<text x="42" y="55" font-size="13" font-weight="650" letter-spacing="1.7" '
        'fill="#52616a">CAPACITIVE MEMS ACCELEROMETER</text>'
    )
    parts.append(
        '<text x="42" y="76" font-size="11" fill="#87949b">'
        "released silicon die · differential comb readout</text>"
    )
    for i, label in enumerate(labels):
        x = 48 + i * 112
        col = "#16839a" if i == active else "#a8b2b8"
        parts.append(f'<circle cx="{x}" cy="555" r="5" fill="{col}"/>')
        parts.append(
            f'<text x="{x + 12}" y="559" font-size="11" '
            f'fill="{"#52616a" if i == active else "#909ba1"}">{label}</text>'
        )
        if i < 3:
            parts.append(f'<path d="M{x + 76} 555 H{x + 101}" stroke="#c9d1d5" stroke-width="1"/>')
    parts.append("</g>")
    parts.append(
        f'<g font-family="ui-monospace, SFMono-Regular, monospace" fill="#52616a">'
        f'<text x="777" y="525" font-size="10">x shift</text>'
        f'<text x="777" y="543" font-size="13">{xshift / INPUT_GAIN:+.2f} µm</text></g>'
    )
    parts.append(
        '<path d="M847 524 H916" stroke="#b5c1c7" stroke-width="1"/>'
        '<path d="M847 520 V528 M881 521 V527 M916 520 V528" '
        'stroke="#71818a" stroke-width="1"/>'
    )
    parts.append(
        '<text x="846" y="541" font-family="system-ui,sans-serif" font-size="9" '
        'fill="#87949b">-5</text>'
        '<text x="909" y="541" font-family="system-ui,sans-serif" font-size="9" '
        'fill="#87949b">+5</text>'
    )
    metadata = (
        f"Capacitive MEMS accelerometer cutaway, stage {stage}; proof mass shifted "
        f"{xshift / INPUT_GAIN:+.2f} micrometres (illustrative exaggerated motion)."
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        'role="img" aria-labelledby="imu-title imu-desc">'
        '<title id="imu-title">Capacitive MEMS accelerometer cutaway</title>'
        f'<desc id="imu-desc">{escape(metadata)} Isometric package and silicon die expose '
        "fixed and moving comb fingers, suspension flexures, anchors, wire bonds and "
        "differential readout.</desc>" + "".join(parts) + "</svg>"
    )
