"""Exterior openings of the existing SovietSchool model, recomputed from the Go generator
(tools/cmd/build/facades.go, entblock.go, rear.go) so the interior lines up exactly."""
from dataclasses import dataclass
from .params import *


@dataclass
class ExtWindow:
    facade: str        # main_front, main_rear, end_w, end_e, eb_w, eb_e, eb_s
    axis: str          # "x": wall runs along X (s = world X); "y": along Y (s = world Y)
    plane: float       # facade plane coordinate
    face: float        # interior wall face coordinate
    inward: int        # +1 / -1 : direction from facade into the building along the normal axis
    s: float           # centre along the wall (world coordinate)
    hw: float          # half width of the glass opening
    z0: float
    z1: float
    kind: str          # std / hall
    level: int         # storey index (0..3); hall windows -> 1

    @property
    def glass(self):
        return self.plane + self.inward * GLASS_RECESS


def _std(f, axis, plane, face, inward, s, zb, lvl):
    return ExtWindow(f, axis, plane, face, inward, s, STD_HALF_W, zb + STD_Z0, zb + STD_Z1, "std", lvl)


def exterior_windows():
    out = []
    for f, lv in enumerate(LEVELS):
        zb = lv + WIN_BASE
        for k in range(MAIN_BAYS):
            if not (9 <= k <= 12 and f <= 2):
                out.append(_std("main_front", "x", 0.0, EXT_T, +1, k * BAY + BAY / 2, zb, f))
            x = MAIN_LEN - (k * BAY + BAY / 2)
            if not (f == 0 and k in (1, 23)):
                out.append(_std("main_rear", "x", MAIN_DEPTH, MAIN_DEPTH - EXT_T, -1, x, zb, f))
        out.append(_std("end_w", "y", 0.0, EXT_T, +1, MAIN_DEPTH / 2, zb, f))
        out.append(_std("end_e", "y", MAIN_LEN, MAIN_LEN - EXT_T, -1, MAIN_DEPTH / 2, zb, f))
    g = FFL + WIN_BASE
    for k in (4, 5):
        out.append(_std("eb_w", "y", ENT_X0, ENT_IX0, +1, -(k * HALL_BAY + HALL_BAY / 2), g, 0))
    for k in range(6):
        out.append(_std("eb_e", "y", ENT_X1, ENT_IX1, -1, ENT_Y0 + k * HALL_BAY + HALL_BAY / 2, g, 0))
        for f, plane, face, inw in (("eb_w", ENT_X0, ENT_IX0, +1), ("eb_e", ENT_X1, ENT_IX1, -1)):
            s = -(k * HALL_BAY + HALL_BAY / 2) if f == "eb_w" else ENT_Y0 + k * HALL_BAY + HALL_BAY / 2
            out.append(ExtWindow(f, "y", plane, face, inw, s, HALL_HALF_W, HALL_BASE + HALL_Z0,
                                 HALL_BASE + HALL_Z1, "hall", 1))
    cx = (ENT_X0 + ENT_X1) / 2
    for zb, lv in ((g, 0), (5.6, 1), (8.7, 1)):
        out.append(_std("eb_s", "x", ENT_Y0, ENT_IY0, +1, cx, zb, lv))
    return out
