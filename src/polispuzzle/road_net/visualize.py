"""Visualization utilities for road networks."""

import geopandas as gpd
import matplotlib.pyplot as plt
import osmnx as ox
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

__all__ = ["plotNetwork"]


def plotNetwork(graph, study_area, *, figsize=(10, 10), show=True):
    """Plot the study and model portions of a road graph.

    Parameters
    ----------
    graph : networkx.MultiDiGraph
        An OSMnx-compatible road network.
    study_area : str or path-like
        Name shown as the map title.
    figsize : tuple, default (10, 10)
        Figure width and height in inches.
    show : bool, default True
        Display the figure immediately when true.

    Returns
    -------
    tuple
        ``(nodes, links, figure, axes)`` for further inspection or styling.
    """
    nodes, links = ox.graph_to_gdfs(graph)

    figure, axes = plt.subplots(figsize=figsize, dpi=500)

    model_polygon = graph.graph.get("model_area_polygon")
    study_polygon = graph.graph.get("study_area_polygon")
    if model_polygon is not None:
        gpd.GeoSeries([model_polygon], crs=graph.graph["crs"]).plot(
            ax=axes, facecolor="orange", edgecolor="darkorange",
            alpha=0.18, linewidth=1, zorder=0,
        )
    if study_polygon is not None:
        gpd.GeoSeries([study_polygon], crs=graph.graph["crs"]).plot(
            ax=axes, facecolor="deepskyblue", edgecolor="dodgerblue",
            alpha=0.18, linewidth=1, zorder=1,
        )

    links.plot(ax=axes, color="grey", linewidth=0.6, zorder=2)
    nodes.plot(ax=axes, color="blue", markersize=4, zorder=3)

    legend_items = [
        Patch(
            facecolor="deepskyblue", edgecolor="dodgerblue", alpha=0.18,
            label="Study area",
        ),
        Patch(
            facecolor="orange", edgecolor="darkorange", alpha=0.18,
            label="Model area",
        ),
        Line2D([0], [0], color="grey", linewidth=2, label="Links"),
        Line2D(
            [0], [0], marker="o", linestyle="none", color="blue",
            markersize=5, label="Nodes",
        ),
    ]
    axes.legend(handles=legend_items, loc="best")

    axes.set_title(str(study_area))
    axes.grid(True)
    axes.set_axisbelow(True)
    figure.tight_layout()

    if show:
        plt.show()

    return nodes, links, figure, axes
