"""Make the map of the world of the page Countries: static/maps/world.svg.

Usage: ``make world-map``. It reads the countries of Natural Earth (public domain, 1:50m,
version NATURAL_EARTH) and writes one path per country, by its ISO code, with the point of
its label and its area, so that the page can find small countries near the pointer.

Run it again only to change the map; the SVG is part of the repository.
"""

import json
import math
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from community_insights.locations.projection import WIDTH, project  # noqa: E402

NATURAL_EARTH = "v5.1.2"
SOURCE = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    f"{NATURAL_EARTH}/geojson/ne_50m_admin_0_countries.geojson"
)
OUTPUT = ROOT / "static" / "maps" / "world.svg"
TOLERANCE = 0.35  # units of the map (1000 wide) a simplified line may be off
SMALLEST_RING = 0.08  # islands smaller than this area are left out, unless they are all
# shapes of Natural Earth without an ISO code of their own, by their name
CODES = {"Somaliland": "SO", "N. Cyprus": "CY", "Siachen Glacier": "IN"}
LEFT_OUT = {"AQ"}  # Antarctica: nobody lives there, the map ends further north
SOUTH = -58  # degrees: the map ends below Cape Horn


def code_of(properties: dict) -> str | None:
    """The ISO 3166 code of a shape of Natural Earth.

    Args:
        properties: The properties of the shape.

    Returns:
        The two letters, or None for a shape that has none.

    Examples:
        >>> code_of({"ISO_A2_EH": "FR", "NAME": "France"})
        'FR'
        >>> code_of({"ISO_A2_EH": "-99", "NAME": "N. Cyprus"})
        'CY'
    """
    code = properties.get("ISO_A2_EH")
    if code and code != "-99":
        return code
    return CODES.get(properties.get("NAME", ""))


def area(points: list[tuple[float, float]]) -> float:
    """The area of a ring of points, without its sign (shoelace formula).

    Args:
        points: The ring.

    Returns:
        The area.

    Examples:
        >>> area([(0, 0), (2, 0), (2, 2), (0, 2)])
        4.0
    """
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1], strict=True):
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Fewer points of a line that stays within a tolerance (Ramer-Douglas-Peucker).

    Args:
        points: The line.
        tolerance: How far the simplified line may be from a point left out.

    Returns:
        The points kept, the first and the last among them.

    Examples:
        >>> simplify([(0, 0), (1, 0.01), (2, 0)], 0.1)
        [(0, 0), (2, 0)]
    """
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        (x1, y1), (x2, y2) = points[first], points[last]
        length = math.hypot(x2 - x1, y2 - y1)
        farthest, index = 0.0, 0
        for i in range(first + 1, last):
            x, y = points[i]
            if length:
                distance = abs((x2 - x1) * (y1 - y) - (x1 - x) * (y2 - y1)) / length
            else:
                distance = math.hypot(x - x1, y - y1)
            if distance > farthest:
                farthest, index = distance, i
        if farthest > tolerance:
            keep[index] = True
            stack += [(first, index), (index, last)]
    return [p for p, kept in zip(points, keep, strict=True) if kept]


def rings(geometry: dict) -> list[list[tuple[float, float]]]:
    """The projected outer rings and holes of a polygon or multipolygon.

    Args:
        geometry: The GeoJSON geometry.

    Returns:
        The rings, on the map.
    """
    polygons = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        polygons = [polygons]
    found = []
    for polygon in polygons:
        for ring in polygon:
            points = [project(lon, lat) for lon, lat in ring]
            found.append([p for i, p in enumerate(points) if i == 0 or p != points[i - 1]])
    return found


def path(shapes: list[list[tuple[float, float]]]) -> str:
    """The SVG path of rings.

    Args:
        shapes: The rings.

    Returns:
        The ``d`` of a path.

    Examples:
        >>> path([[(0.0, 1.5), (2.0, 1.5), (2.0, 3.0)]])
        'M0 1.5L2 1.5L2 3Z'
    """

    def number(value: float) -> str:
        return f"{value:.1f}".rstrip("0").rstrip(".")

    return "".join(
        "M" + "L".join(f"{number(x)} {number(y)}" for x, y in ring) + "Z" for ring in shapes
    )


def countries(features: list[dict]) -> dict[str, dict]:
    """The path, the label point and the area of each country.

    Args:
        features: The shapes of Natural Earth.

    Returns:
        By ISO code: ``d``, ``x``, ``y`` and ``area``.
    """
    found: dict[str, dict] = {}
    for feature in features:
        properties = feature["properties"]
        code = code_of(properties)
        if not code or code in LEFT_OUT:
            continue
        country = found.setdefault(code, {"rings": [], "label": None, "home": -1})
        country["rings"] += rings(feature["geometry"])
        # the label of the main part, such as France and not French Guiana
        rank = properties.get("POP_EST") or 0
        if rank > country["home"]:
            country["home"] = rank
            country["label"] = project(properties["LABEL_X"], properties["LABEL_Y"])
    result = {}
    for code, country in sorted(found.items()):
        simplified = [simplify(ring, TOLERANCE) for ring in country["rings"]]
        simplified = [ring for ring in simplified if len(ring) >= 3] or [
            ring for ring in country["rings"] if len(ring) >= 3
        ]  # a tiny country keeps all its points
        largest = max(simplified, key=area)
        kept = [r for r in simplified if r is largest or area(r) >= SMALLEST_RING]
        x, y = country["label"]
        result[code] = {
            "d": path(kept),
            "x": x,
            "y": y,
            "area": round(sum(area(r) for r in kept), 2),
        }
    return result


def svg(found: dict[str, dict]) -> str:
    """The SVG of the map.

    Args:
        found: The countries, as made by `countries`.

    Returns:
        The SVG.
    """
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '
        f'{WIDTH:g} {project(0, SOUTH)[1]:g}" class="world-map" data-map="">',
        f"<!-- Natural Earth {NATURAL_EARTH}, public domain; made by scripts/world_map.py -->",
        '<g data-countries="">',
    ]
    lines += [
        f'<path data-country="{code}" data-x="{c["x"]:g}" data-y="{c["y"]:g}" '
        f'data-area="{c["area"]:g}" d="{c["d"]}"/>'
        for code, c in found.items()
    ]
    lines += ["</g>", '<g data-places=""></g>', "</svg>", ""]
    return "\n".join(lines)


def main(source: str = SOURCE) -> None:
    """Read Natural Earth and write the map.

    Args:
        source: The address or the file of the GeoJSON.
    """
    if "://" in source:
        with urlopen(source) as answer:  # noqa: S310 - a fixed address of GitHub
            data = json.load(answer)
    else:
        data = json.loads(Path(source).read_text())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg(countries(data["features"])))
    print(f"{OUTPUT.relative_to(ROOT)}: {OUTPUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main(*sys.argv[1:])
