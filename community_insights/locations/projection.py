"""Where a longitude and latitude are on the map of the world: the Equal Earth projection.

Equal Earth (Šavrič, Patterson and Jenny, 2018) keeps the areas of the countries, so a big
country is not drawn bigger than it is. The map is ``WIDTH`` wide, the north at the top.
"""

import math

A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = math.sqrt(3) / 2
WIDTH = 1000.0
# x of the projection at 180 degrees on the equator, y at the poles
X_MAX = 2 * math.sqrt(3) * math.pi / (3 * A1)
POLE = math.pi / 3  # the angle theta of the poles
Y_MAX = A4 * POLE**9 + A3 * POLE**7 + A2 * POLE**3 + A1 * POLE
SCALE = WIDTH / (2 * X_MAX)
HEIGHT = round(2 * Y_MAX * SCALE, 1)


def project(longitude: float, latitude: float) -> tuple[float, float]:
    """The point of the map of a place.

    Args:
        longitude: Degrees east, from -180 to 180.
        latitude: Degrees north, from -90 to 90.

    Returns:
        x from the left and y from the top, rounded to a tenth.

    Examples:
        >>> project(0, 0)
        (500.0, 243.3)
        >>> x, y = project(13.4, 52.5)  # Berlin: right of the middle, above the equator
        >>> x > 500 and y < 243.3
        True
    """
    theta = math.asin(M * math.sin(math.radians(latitude)))
    lam = math.radians(longitude)
    x = (
        2
        * math.sqrt(3)
        * lam
        * math.cos(theta)
        / (3 * (9 * A4 * theta**8 + 7 * A3 * theta**6 + 3 * A2 * theta**2 + A1))
    )
    y = A4 * theta**9 + A3 * theta**7 + A2 * theta**3 + A1 * theta
    return round(WIDTH / 2 + x * SCALE, 1), round(HEIGHT / 2 - y * SCALE, 1)
