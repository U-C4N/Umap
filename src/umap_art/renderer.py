"""Matplotlib delivery adapter; it consumes scenes and never fetches map data."""
from __future__ import annotations

import hashlib
import os
import tempfile
import threading
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path

from matplotlib import rc_context
from matplotlib.artist import Artist
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import PathCollection
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path as MplPath
from matplotlib.text import Text

from .models import Artifact, MapSpec
from .scene import FONT_PATH, Scene

_RENDER_LOCK = threading.RLock()
_MIME_TYPES = {"png": "image/png", "svg": "image/svg+xml", "pdf": "application/pdf"}


class GroupArtist(Artist):
    """Preserve named SVG groups through the official renderer interface."""

    def __init__(self, group_id, children):
        super().__init__()
        self.set_gid(group_id)
        self.children = children

    def draw(self, renderer):
        if not self.get_visible():
            return
        renderer.open_group("umap", gid=self.get_gid())
        for child in self.children:
            child.draw(renderer)
        renderer.close_group("umap")
        self.stale = False

    def get_children(self):
        return list(self.children)


def _figure(scene: Scene, *, raster=False):
    fig = Figure(figsize=(scene.width_pt/72, scene.height_pt/72), layout=None)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, scene.width_pt)
    ax.set_ylim(0, scene.height_pt)
    ax.set_axis_off()
    clip = Rectangle(scene.frame[:2], scene.frame[2], scene.frame[3], transform=ax.transData)
    for group_index, group in enumerate(scene.groups):
        children = []
        if raster:
            # The Agg backend can draw a consecutive run of identical paints in
            # one collection. This avoids one Artist and clip transform per
            # feature, while preserving feature order, holes and alpha blending.
            # Vector formats deliberately retain individually editable paths.
            runs = groupby(group.paths, key=lambda path: (path.paint, path.clip))
            for batch_index, ((paint, clipped), paths) in enumerate(runs):
                batch = []
                for path in paths:
                    mpl_path = MplPath(path.vertices, path.codes)
                    mpl_path.should_simplify = False
                    batch.append(mpl_path)
                collection = PathCollection(batch, facecolors=paint.fill or "none",
                    edgecolors=paint.stroke or "none", linewidths=[paint.width_pt],
                    linestyles=[(0, paint.dash_pt)] if paint.dash_pt else "solid",
                    alpha=paint.opacity, antialiaseds=True, transform=ax.transData,
                    capstyle="round", joinstyle="round")
                collection.set_gid(f"{group.id}-raster-{batch_index}")
                collection.set_figure(fig)
                collection.axes = ax
                if clipped:
                    collection.set_clip_path(clip)
                else:
                    collection.set_clip_on(False)
                children.append(collection)
        for path in (() if raster else group.paths):
            mpl_path = MplPath(path.vertices, path.codes)
            mpl_path.should_simplify = False
            p = path.paint
            artist = PathPatch(mpl_path, facecolor=p.fill or "none", edgecolor=p.stroke or "none",
                               linewidth=p.width_pt, alpha=p.opacity, antialiased=True,
                               transform=ax.transData, capstyle="round", joinstyle="round")
            artist.set_gid(path.id)
            if p.dash_pt:
                artist.set_linestyle((0, p.dash_pt))
            artist.set_figure(fig)
            artist.axes = ax
            if path.clip:
                artist.set_clip_path(clip)
            else:
                artist.set_clip_on(False)
            children.append(artist)
        group_artist = GroupArtist(group.id, children)
        group_artist.set_zorder(group_index)
        ax.add_artist(group_artist)
    for item in scene.texts:
        artist = Text(item.x, item.y, item.text, color=item.color,
                      fontproperties=FontProperties(fname=str(FONT_PATH), size=item.size_pt),
                      horizontalalignment=item.align, verticalalignment="baseline",
                      transform=ax.transData, parse_math=False)
        artist.set_gid(item.id)
        artist.set_zorder(len(scene.groups)+1)
        if item.clip:
            artist.set_clip_path(clip)
        else:
            artist.set_clip_on(False)
        ax.add_artist(artist)
    return fig


def render_scene(scene: Scene, spec: MapSpec, output_dir: Path) -> list[Artifact]:
    """Write requested formats atomically without changing page layout or scale."""
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = []
    settings = {
        "svg.fonttype": "none" if spec.page.text_mode == "editable" else "path",
        "svg.hashsalt": scene.semantic_hash(), "pdf.fonttype": 42,
        "path.simplify": False, "agg.path.chunksize": 0,
        "lines.scale_dashes": False,
        "savefig.bbox": None, "savefig.pad_inches": 0,
        "text.usetex": False,
    }
    # rc_context is process-global; public Python callers get serialization as well.
    with _RENDER_LOCK, rc_context(settings):
        figures = {}
        try:
            for fmt in spec.formats:
                raster = fmt == "png"
                if raster not in figures:
                    figures[raster] = _figure(scene, raster=raster)
                fig = figures[raster]
                destination = output_dir / f"{scene.view}.{fmt}"
                descriptor, name = tempfile.mkstemp(prefix=f".{scene.view}-", suffix=".tmp",
                                                     dir=output_dir)
                os.close(descriptor)
                temporary = Path(name)
                metadata = {"Creator": "umap-art", "Title": spec.title}
                if fmt == "svg":
                    metadata["Date"] = "2000-01-01T00:00:00Z"
                elif fmt == "pdf":
                    metadata["CreationDate"] = datetime(2000, 1, 1, tzinfo=timezone.utc)
                    metadata["ModDate"] = datetime(2000, 1, 1, tzinfo=timezone.utc)
                try:
                    # Nearest integer pixel dimensions are the raster equivalent of
                    # the exact physical page; scene layout itself remains unchanged.
                    if fmt == "png":
                        fig.set_size_inches(round(scene.width_pt/72*spec.page.dpi)/spec.page.dpi,
                                            round(scene.height_pt/72*spec.page.dpi)/spec.page.dpi)
                    else:
                        fig.set_size_inches(scene.width_pt/72, scene.height_pt/72)
                    fig.savefig(temporary, format=fmt, dpi=spec.page.dpi,
                                facecolor="white", transparent=False, metadata=metadata)
                    digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
                    size = temporary.stat().st_size
                    temporary.replace(destination)
                    artifacts.append(Artifact(path=str(destination), mime_type=_MIME_TYPES[fmt],
                                              sha256=digest, size_bytes=size, view=scene.view))
                finally:
                    temporary.unlink(missing_ok=True)
        finally:
            for fig in figures.values():
                fig.clear()
    return artifacts
