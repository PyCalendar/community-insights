"""A badge as data: its JSON spec, drawn as SVG or PNG."""

import io
import json
import os
from dataclasses import dataclass, field

from django.http import Http404, HttpResponse

from .badges import badge
from .heavy import LOCK

HEIGHT, PADDING, SCALE = 20, 6, 2  # pixels of the badge; the PNG is drawn twice as large
LABEL_COLOR = "#555"
FORMATS = {"svg": "image/svg+xml", "png": "image/png", "json": "application/json"}


@dataclass
class BadgeSpec:
    """What a badge says: a label, a message and a colour, and data besides.

    Every badge of the site is made from such a spec: as JSON (the format of shields.io's
    endpoint badges with the data besides), as SVG, or as PNG.

    Attributes:
        label: The text of the left side.
        message: The text of the right side.
        color: The colour of the right side, such as ``#2da44e``.
        data: More of what the badge counts, added to the JSON.
    """

    label: str
    message: str
    color: str
    data: dict = field(default_factory=dict)

    def json(self) -> dict:
        """The spec as JSON: shields.io can draw it (https://shields.io/badges/endpoint-badge).

        Returns:
            The data.

        Examples:
            >>> BadgeSpec("PR response", "3h", "#2a7de1", {"n": 5}).json()["message"]
            '3h'
        """
        return {
            "schemaVersion": 1,
            "label": self.label,
            "message": self.message,
            "color": self.color,
            **self.data,
        }

    def svg(self) -> bytes:
        """The badge as SVG, with a title for screen readers.

        Returns:
            The SVG.
        """
        return badge(self.label, self.message, self.color)

    def png(self) -> bytes:
        """The badge as PNG, drawn twice as large as the SVG, for sharp screens.

        Returns:
            The PNG.

        Examples:
            >>> BadgeSpec("a", "b", "#2da44e").png()[1:4]
            b'PNG'
        """
        with LOCK:  # see heavy.py
            from matplotlib import get_data_path
            from PIL import Image, ImageDraw, ImageFont

        font = ImageFont.truetype(
            os.path.join(get_data_path(), "fonts", "ttf", "DejaVuSans.ttf"), 11 * SCALE
        )
        widths = [
            round(font.getlength(text)) + 2 * PADDING * SCALE for text in (self.label, self.message)
        ]
        height = HEIGHT * SCALE
        image = Image.new("RGBA", (sum(widths), height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((0, 0, sum(widths) - 1, height - 1), 3 * SCALE, fill=self.color)
        draw.rounded_rectangle(
            (0, 0, widths[0] + 3 * SCALE, height - 1), 3 * SCALE, fill=LABEL_COLOR
        )
        draw.rectangle((widths[0], 0, widths[0] + 3 * SCALE, height - 1), fill=self.color)
        for left, width, text in ((0, widths[0], self.label), (widths[0], widths[1], self.message)):
            draw.text((left + width / 2, height / 2), text, font=font, fill="white", anchor="mm")
        found = io.BytesIO()
        image.save(found, format="PNG", optimize=True)
        return found.getvalue()

    def response(self, extension: str, max_age: int) -> HttpResponse:
        """The badge in a format, kept by browsers and proxies for a time.

        Args:
            extension: ``svg``, ``png`` or ``json``.
            max_age: Seconds browsers and proxies may keep it.

        Returns:
            The response; JSON can be read by pages of other sites.

        Raises:
            Http404: For another format.
        """
        if extension not in FORMATS:
            raise Http404("Badges are svg, png or json")
        if extension == "json":
            content = json.dumps(self.json(), ensure_ascii=False).encode()
        else:
            content = self.svg() if extension == "svg" else self.png()
        response = HttpResponse(content, content_type=FORMATS[extension])
        response["Cache-Control"] = f"public, max-age={max_age}"
        if extension == "json":
            response["Access-Control-Allow-Origin"] = "*"
        return response
