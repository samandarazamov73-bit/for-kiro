"""Local frame and dimensions of the U-shaped stair module (shared by plan drawing and 3D)."""
from .params import *

# local frame: u along the flights (0 = floor-landing end wall), v across (0 = corridor-side wall)
CELL_U = 5.88
CELL_V = 6.15


def stair_frame(room):
    """Returns f(u, v) -> (x, y) for one of the three stair cells."""
    x0, x1, y0, y1 = room.rects[0]
    if room.rid.endswith("STAIR1"):        # main stair: corridor at y1, flights run +X
        return lambda u, v: (x0 + u, y1 - v)
    if room.rid.endswith("STAIR2"):        # west stair: corridor at y0, flights run +X
        return lambda u, v: (x0 + u, y0 + v)
    return lambda u, v: (x1 - u, y0 + v)   # east stair: flights run -X


def stair_spec():
    L = STAIR_LANDING
    a = (0.0, FLIGHT_W)                              # flight A (up from the floor landing)
    b = (FLIGHT_W + FLIGHT_GAP, 2 * FLIGHT_W + FLIGHT_GAP)  # flight B (up from the mid-landing)
    return {
        "floor_landing": ((0.0, L), (0.0, b[1])),
        "mid_landing": ((L + STAIR_RUN, CELL_U), (0.0, b[1])),
        "lobby": ((0.0, CELL_U), (b[1], CELL_V)),       # floor-level zone beside the windows / hall
        "flights": [
            {"u": (L, L + STAIR_RUN), "v": a, "dir": +1},
            {"u": (L + STAIR_RUN, L), "v": b, "dir": -1},
        ],
        "void": ((L, CELL_U), (0.0, b[1])),
    }
