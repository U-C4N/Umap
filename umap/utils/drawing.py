"""Drawing utilities for Umap."""
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import math


def add_frame(ax, linewidth: float = 0.5, color: str = 'black') -> None:
    """Add a minimalist frame to the plot."""
    if ax is None:
        return
    
    ax.set_frame_on(False)
    ax.add_patch(
        Rectangle(
            (0, 0), 1, 1, transform=ax.transAxes,
            fill=False, color=color, linewidth=linewidth,
            clip_on=False,
        )
    )


def add_north_arrow(ax, location=(0.95, 0.92), size=0.06, color='black') -> None:
    """Draw a simple north arrow in axes coordinates."""
    if ax is None:
        return
    x, y = location
    ax.annotate(
        "",
        xy=(x, y), xytext=(x, y - size),
        xycoords=ax.transAxes,
        arrowprops=dict(facecolor=color, edgecolor=color, width=2, headwidth=10, headlength=10),
    )
    ax.text(x, y + 0.015, "N", transform=ax.transAxes, ha='center', va='bottom', color=color)


def add_scale_bar(ax, length_km: float = 1.0, location=(0.08, 0.08), color='black') -> None:
    """Add an approximate scale bar using degrees-to-meters at map center latitude."""
    if ax is None or length_km <= 0:
        return
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    lat_center = (ylim[0] + ylim[1]) / 2.0
    meters_per_deg_lon = 111320 * max(math.cos(math.radians(lat_center)), 1e-6)
    delta_lon = (length_km * 1000.0) / meters_per_deg_lon

    x0 = xlim[0] + (xlim[1] - xlim[0]) * location[0]
    y0 = ylim[0] + (ylim[1] - ylim[0]) * location[1]
    x1 = x0 + delta_lon

    ax.plot([x0, x1], [y0, y0], color=color, lw=2, solid_capstyle='butt')
    ax.plot([x0, x0], [y0 - (ylim[1]-ylim[0]) * 0.005, y0 + (ylim[1]-ylim[0]) * 0.005], color=color, lw=1)
    ax.plot([x1, x1], [y0 - (ylim[1]-ylim[0]) * 0.005, y0 + (ylim[1]-ylim[0]) * 0.005], color=color, lw=1)
    ax.text((x0 + x1) / 2.0, y0 + (ylim[1]-ylim[0]) * 0.008, f"{int(length_km)} km", ha='center', va='bottom', color=color)


def add_poster_layout(ax, title: str, subtitle: str = None, color: str = '#1f2937') -> None:
    """Add a classic map-poster footer: rule line, spaced city name, subtitle.

    Text is drawn below the axes in axes coordinates so it survives
    ``savefig(bbox_inches='tight')`` regardless of figure margins.
    """
    if ax is None or not title:
        return

    spaced_title = " ".join(title.upper())

    ax.plot(
        [0.38, 0.62], [-0.050, -0.050],
        transform=ax.transAxes, color=color,
        lw=0.8, clip_on=False, solid_capstyle='butt',
    )
    ax.text(
        0.5, -0.115, spaced_title,
        transform=ax.transAxes, ha='center', va='center',
        fontsize=30, family='serif', color=color, clip_on=False,
    )
    if subtitle:
        ax.text(
            0.5, -0.165, subtitle,
            transform=ax.transAxes, ha='center', va='center',
            fontsize=10, family='serif', color=color, alpha=0.75,
            clip_on=False,
        )


def format_center_coords(ax) -> str:
    """Format the map center as a poster-style coordinate string."""
    if ax is None:
        return ""
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    lon = (xlim[0] + xlim[1]) / 2.0
    lat = (ylim[0] + ylim[1]) / 2.0
    ns = 'N' if lat >= 0 else 'S'
    ew = 'E' if lon >= 0 else 'W'
    return f"{abs(lat):.4f}\u00b0 {ns}  /  {abs(lon):.4f}\u00b0 {ew}"


def add_legend_simple(ax, style: dict, text_color: str = 'black') -> None:
    """Add a minimal legend using current style colors."""
    if ax is None:
        return
    handles = []
    if 'streets' in style:
        handles.append(mlines.Line2D([], [], color=style['streets'].get('ec', '#000'), lw=2, label='Yollar'))
    if 'bridges' in style:
        handles.append(mlines.Line2D([], [], color=style['bridges'].get('ec', '#b00'), lw=2, label='K\u00f6pr\u00fcler'))
    if 'water' in style:
        handles.append(mpatches.Patch(facecolor=style['water'].get('fc', '#aaf'), edgecolor=style['water'].get('ec', '#55f'), label='Su'))
    if 'building' in style:
        building_style = style['building']
        handles.append(mpatches.Patch(
            facecolor=building_style.get('fc', building_style.get('extrude', {}).get('roof_fc', '#ddd')),
            edgecolor=building_style.get('ec', building_style.get('extrude', {}).get('roof_ec', '#333')),
            label='Binalar',
        ))

    if handles:
        ax.legend(handles=handles, loc='lower right', frameon=False, labelcolor=text_color)
