"""Whether a seat hides a legless bust: read on rendered masks, because the rig's own keys, not its rest pose, say how
far its base rises. The base is the figure's lowest rows; a column of it the near edge does not cover is a base in view.
"""

import numpy as np

SOLID = 128
BASE_ROWS = 40  # how far above a figure's lowest pixel still counts as its base


def exposed_columns(figure_alpha: np.ndarray, near_alpha: np.ndarray) -> int:
    """How many columns show the figure's base: its last pixel in the column lies in the base rows and is not under the
    near edge. A column where the figure ends higher up is its side or an arm, not its base."""
    figure, near = figure_alpha >= SOLID, near_alpha >= SOLID
    filled = figure.any(axis=0)
    if not filled.any():
        return 0
    lowest = figure.shape[0] - 1 - np.argmax(figure[::-1], axis=0)
    base = lowest[filled].max() - BASE_ROWS
    columns = np.flatnonzero(filled & (lowest >= base))
    return int(np.count_nonzero(~near[lowest[columns], columns]))


def clearance(figure_alpha: np.ndarray, near_alpha: np.ndarray) -> int:
    """Rows from the top of the near edge down to the figure's base, the least over the columns of its base: above 0 the
    edge overlaps the base, at or below 0 it does not reach it."""
    figure, near = figure_alpha >= SOLID, near_alpha >= SOLID
    filled = figure.any(axis=0)
    if not filled.any():
        return figure.shape[0]
    lowest = figure.shape[0] - 1 - np.argmax(figure[::-1], axis=0)
    base = lowest[filled].max() - BASE_ROWS
    columns = np.flatnonzero(filled & (lowest >= base))
    tops = np.where(near[:, columns].any(axis=0), np.argmax(near[:, columns], axis=0), figure.shape[0])
    return int((lowest[columns] - tops).min())
