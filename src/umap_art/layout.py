"""One physical layout contract for extent calculation and scene compilation.

All values are millimetres from the page's bottom-left. The two poster layouts
reserve six 5 mm rows in a 36 mm band, even with no places. Editing place content
or typography therefore cannot change the acquired extent or physical scale.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .errors import UmapError

if TYPE_CHECKING:
    from .models import PageSpec


@dataclass(frozen=True)
class PageLayout:
    frame_mm: tuple[float, float, float, float]
    title_band_mm: tuple[float, float, float, float]
    places_band_mm: tuple[float, float, float, float] | None


def resolve_layout(page: PageSpec) -> PageLayout:
    w, h = page.dimensions_mm
    m, header, footer = page.margin_mm, page.header_mm, page.footer_mm
    width = w - 2*m
    if page.layout == "classic":
        frame = (m, m+footer, width, h-2*m-header-footer)
        title = (m, h-m-header, width, header)
        places = None
    else:
        places = (m, m+footer, width, 36.0)
        height = h-2*m-header-footer-36.0
        if page.layout == "poster":
            title = (m, m+footer+36.0, width, header)
            frame = (m, title[1]+header, width, height)
        else:
            frame = (m, m+footer+36.0, width, height)
            title = (m, frame[1]+height, width, header)
    if min(frame[2:]) <= 0:
        raise UmapError("INVALID_PAGE", "Information bands leave no positive map frame")
    return PageLayout(frame, title, places)
