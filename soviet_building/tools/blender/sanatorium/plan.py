"""Floor plan data of the sanatorium interior.

Rooms are described by their clear (inside-face) rectangles. Walls are the gaps
between rectangles of different rooms; rectangles that touch with zero gap are
open to each other. Everything here is plain data so that the same source drives
the 3D build (build_sanatorium.py) and the 2D plan drawings (drawplan.py).
"""
from dataclasses import dataclass, field
from .params import *

FRONT, REAR = "front", "rear"


@dataclass
class Room:
    rid: str                  # unique id, e.g. "L0.F14"
    num: str                  # number on the door sign ("" = none)
    ru: str                   # Russian name (signs)
    en: str                   # English name (docs)
    level: int                # 0..3 (multi-level spaces use their lowest level)
    rects: list               # [(x0, x1, y0, y1), ...]
    kind: str                 # furnishing recipe
    dept: str                 # A_entrance, B_admin, C_medical, D_catering, E_technical, P_patient, CIRC
    wall: str = "paint_beige"
    floor: str = "linoleum_brown"
    ceil: str = "ceiling"
    z0: float = None
    z1: float = None
    win: str = None           # window side for the local furnishing frame
    skip: list = field(default_factory=list)   # [(edge, coord, a, b, z0, z1)] faces not to build
    upper_wall: str = "plaster"  # material above CEIL_H in tall rooms
    seed: int = 0

    def __post_init__(self):
        if self.z0 is None:
            self.z0 = LEVELS[self.level]
        if self.z1 is None:
            self.z1 = self.z0 + CEIL_H

    @property
    def bbox(self):
        xs = [r[0] for r in self.rects] + [r[1] for r in self.rects]
        ys = [r[2] for r in self.rects] + [r[3] for r in self.rects]
        return min(xs), max(xs), min(ys), max(ys)

    @property
    def area(self):
        return sum((r[1] - r[0]) * (r[3] - r[2]) for r in self.rects)


@dataclass
class Door:
    level: int
    a: str                    # room id
    b: str                    # room id or "EXT"
    c: float                  # centre along the wall (world coordinate)
    w: float = 0.9            # leaf width (double doors: total)
    kind: str = "std"         # std, glazed, double, metal, steel_double, wide, opening, window, counter, port, wc
    hinge: str = "l"
    swing: str = "a"          # leaf opens into room a or b
    ang: float = 0.0          # opening angle in degrees (0 = closed)
    h: float = 2.1            # leaf/opening height
    sill: float = 0.0         # bottom above floor (windows / counters)
    axis: str = None          # wall direction: "x" = wall runs along X (c is an X value), "y" = along Y
    ext: tuple = None         # for EXT doors: (axis, face coordinate)
    sign: bool = True


# ----------------------------------------------------------------------------
def slot(side, k0, k1=None):
    """Clear rectangle of main-wing bays k0..k1 on the front or rear side."""
    k1 = k0 if k1 is None else k1
    x0, _ = bay_x(k0)
    _, x1 = bay_x(k1)
    if side == FRONT:
        return (x0, x1, FRONT_Y0, FRONT_Y1)
    return (x0, x1, REAR_Y0, REAR_Y1)


INNER_D = 2.6     # depth of the corridor-side zone of split bays
INNER_W = 1.6     # width of an inner room in an L-split bay


def split_L(side, k):
    """Bay split into an inner windowless room (west part of the corridor zone)
    and an L-shaped outer room reached by a 1.16 m passage. Returns (outer, inner, cx_outer, cx_inner)."""
    x0, x1, y0, y1 = slot(side, k)
    xi = x0 + min(INNER_W, x1 - x0 - PART_T - 1.16)   # end bays are narrower (exterior wall)
    if side == FRONT:
        yi = y1 - INNER_D
        inner = [(x0, xi, yi, y1)]
        outer = [(x0, x1, y0, yi - PART_T), (xi + PART_T, x1, yi - PART_T, y1)]
    else:
        yi = y0 + INNER_D
        inner = [(x0, xi, y0, yi)]
        outer = [(x0, x1, yi + PART_T, y1), (xi + PART_T, x1, y0, yi + PART_T)]
    return outer, inner, (xi + PART_T + x1) / 2, (x0 + xi) / 2


def split_FB(side, k, depth=INNER_D):
    """Bay split front/back: inner room on the corridor, outer room behind it (walk-through)."""
    x0, x1, y0, y1 = slot(side, k)
    if side == FRONT:
        return [(x0, x1, y0, y1 - depth - PART_T)], [(x0, x1, y1 - depth, y1)]
    return [(x0, x1, y0 + depth + PART_T, y1)], [(x0, x1, y0, y0 + depth)]


def bay_cx(k0, k1=None):
    k1 = k0 if k1 is None else k1
    return (bay_x(k0)[0] + bay_x(k1)[1]) / 2


# ----------------------------------------------------------------------------
class Plan:
    def __init__(self):
        self.rooms = {}
        self.doors = []
        self._num = {}

    def room(self, lvl, key, ru, en, rects, kind, dept, numbered=True, **kw):
        rid = f"L{lvl}.{key}"
        num = ""
        if numbered:
            n = self._num.get(lvl, 0) + 1
            self._num[lvl] = n
            num = f"{lvl + 1}{n:02d}"
        r = Room(rid, num, ru, en, lvl, rects, kind, dept, seed=len(self.rooms) * 7919 + 13, **kw)
        self.rooms[rid] = r
        return r

    def door(self, lvl, a, b, c, **kw):
        d = Door(lvl, f"L{lvl}.{a}" if not a.startswith("L") else a,
                 b if b == "EXT" or b.startswith("L") else f"L{lvl}.{b}", c, **kw)
        self.doors.append(d)
        return d

    # convenience: a whole bay (or bays) room with a corridor door
    def bay_room(self, lvl, side, k0, k1, ru, en, kind, dept, door_c=None, door_kw=None, **kw):
        key = f"{'F' if side == FRONT else 'R'}{k0}"
        r = self.room(lvl, key, ru, en, [slot(side, k0, k1)], kind, dept, win=side, **kw)
        if door_c is not False:
            c = bay_cx(k0, k1) if door_c is None else door_c
            self.door(lvl, key, self.corridor_at(lvl, c), c, **(door_kw or {}))
        return r

    def corridor_at(self, lvl, x):
        if lvl == 0 and x < 15.0:
            return "SC"
        return "C"


SIDE_KEY = {FRONT: "F", REAR: "R"}
BATH_W, BATH_D = 1.9, 2.4          # en-suite bathroom of a 2-bay room


def suite_rects(side, k0, k1, bw=BATH_W, bd=BATH_D):
    """2-bay room with an en-suite bathroom in the corridor-side corner (west end).
    Returns (room_rects, bath_rect, corridor_door_c, bath_door_c)."""
    x0, _ = bay_x(k0)
    _, x1 = bay_x(k1)
    if side == FRONT:
        yb0, yb1 = FRONT_Y1 - bd, FRONT_Y1
        room = [(x0, x1, FRONT_Y0, yb0 - PART_T), (x0 + bw + PART_T, x1, yb0 - PART_T, FRONT_Y1)]
    else:
        yb0, yb1 = REAR_Y0, REAR_Y0 + bd
        room = [(x0, x1, yb1 + PART_T, REAR_Y1), (x0 + bw + PART_T, x1, REAR_Y0, yb1 + PART_T)]
    return room, (x0, x0 + bw, yb0, yb1), x0 + bw + PART_T + 0.75, (yb0 + yb1) / 2


def build_plan():
    P = Plan()
    # ======================= GROUND FLOOR (level 0) ==========================
    L = 0
    P.room(L, "SC", "Служебный коридор пищеблока", "Catering service corridor",
           [(MAIN_X0, 15.0 - PART_T / 2, CORR_Y0, CORR_Y1)], "service_corridor", "CIRC",
           numbered=False, floor="tile_floor", wall="tile_wall")
    P.room(L, "C", "Коридор 1-го этажа", "Ground floor corridor",
           [(15.0 + PART_T / 2, MAIN_X1, CORR_Y0, CORR_Y1)], "corridor", "CIRC",
           numbered=False, floor="terrazzo", wall="paint_beige")
    P.door(L, "SC", "C", 8.1, w=1.4, kind="double", axis="y", ang=0)

    # --- entrance block ---
    P.room(L, "EB_VEST", "Тамбур", "Entrance vestibule",
           [(GLAZ_X + 0.05, 30.0, -REC_S1 + PART_T, -REC_S0 - PART_T)], "vestibule", "A_entrance",
           numbered=False, floor="terrazzo", wall="paint_beige", win="west",
           skip=[("x0", None, None, None, FFL, REC_TOP_Z)])
    P.room(L, "EB_HALL", "Вестибюль и зона ожидания", "Reception hall and waiting area",
           [(30.12, 34.95, -13.0, 0.0), (ENT_IX0, 30.12, -REC_S0, 0.0), (27.06, 29.94, 0.0, CORR_Y0)],
           "hall", "A_entrance", numbered=False, floor="terrazzo", wall="paint_peach")
    P.room(L, "EB_BAR", "Фитобар и бювет минеральных вод", "Phyto-bar and mineral water buvette",
           [(ENT_IX0, 34.95, ENT_IY0, -13.0), (ENT_IX0, 30.12, -13.0, -REC_S1)],
           "phytobar", "S_spa", numbered=False, floor="linoleum_parquet", wall="paint_peach", win="south")
    ex0, ex1 = 35.07, ENT_IX1
    P.room(L, "EB_E1", "Камера хранения багажа", "Luggage storage", [(ex0, ex1, ENT_IY0, -16.31)],
           "luggage", "A_entrance", win="east", floor="linoleum_brown")
    P.room(L, "EB_E2", "Гардероб", "Visitor coatroom", [(ex0, ex1, -16.19, -13.06)],
           "coatroom", "A_entrance", win="east", floor="linoleum_brown")
    P.room(L, "EB_E3", "Регистратура", "Registration / reception desk", [(ex0, ex1, -12.94, -6.56)],
           "registration", "A_entrance", win="east", wall="wallpaper_a", floor="linoleum_parquet")
    P.room(L, "EB_E5", "Справочное бюро", "Information desk", [(ex0, ex1, -6.44, -3.31)],
           "info", "A_entrance", win="east", floor="linoleum_parquet", wall="paint_beige")
    P.room(L, "EB_E6", "Комната охраны", "Security / guard room", [(ex0, ex1, -3.19, -0.06)],
           "guard", "A_entrance", win="east", wall="paint_beige")
    for yc in (-4.275, -8.325):
        P.door(L, "EB_VEST", "EB_HALL", yc, w=1.35, kind="double_glazed", axis="y", ang=0)
    for yc, w in ((-10.4, 1.9), (-6.3, 1.9), (-2.25, 2.0)):
        P.door(L, "EB_VEST", "EB_HALL", yc, w=w, kind="window", sill=0.9, h=1.7, axis="y", sign=False)
    P.door(L, "EB_E1", "EB_BAR", -17.2, w=0.8, kind="std", ang=0)
    P.door(L, "EB_E1", "EB_BAR", -18.45, w=1.0, kind="counter", sill=0.95, h=1.0, sign=False)
    P.door(L, "EB_E2", "EB_BAR", -14.1, w=1.8, kind="counter", sill=0.95, h=1.15, sign=False)
    P.door(L, "EB_E2", "EB_BAR", -15.6, w=0.8, kind="std", ang=0, sign=False)
    P.door(L, "EB_E3", "EB_HALL", -11.6, w=1.4, kind="window", sill=0.95, h=1.35, sign=False)
    P.door(L, "EB_E3", "EB_HALL", -9.6, w=1.4, kind="window", sill=0.95, h=1.35, sign=False)
    P.door(L, "EB_E3", "EB_HALL", -7.3, w=0.9, kind="glazed", ang=0)
    P.door(L, "EB_E5", "EB_HALL", -5.2, w=1.2, kind="window", sill=0.95, h=1.25, sign=False)
    P.door(L, "EB_E5", "EB_HALL", -3.85, w=0.8, kind="std", ang=0)
    P.door(L, "EB_E6", "EB_HALL", -2.2, w=1.2, kind="window", sill=0.9, h=1.2, sign=False)
    P.door(L, "EB_E6", "EB_HALL", -0.75, w=0.8, kind="std", ang=0)

    # --- centre: main stair, elevator, machine room ---
    P.room(L, "STAIR1", "Лестница №1", "Main staircase", [(30.06, 35.94, FRONT_Y0, FRONT_Y1)],
           "stair_main", "CIRC", numbered=False, z1=LEVELS[3] + CEIL_H, wall="paint_beige", floor="terrazzo")
    P.room(L, "SHAFT", "Шахта лифта", "Elevator shaft", [(SHAFT[0], SHAFT[1], SHAFT[2], SHAFT[3])],
           "shaft", "CIRC", numbered=False, z0=SHAFT_PIT_Z, z1=SHAFT_TOP_Z, wall="concrete", floor="concrete",
           ceil="concrete")
    P.room(L, "F12", "Машинное помещение лифта", "Elevator machine room (lower)",
           [(36.06, 38.94, FRONT_Y0, 3.5)], "machine_room", "E_technical", wall="plaster", floor="concrete")
    P.door(L, "F12", "EB_E6", 37.6, w=0.8, kind="metal", sign=True)
    P.door(L, "STAIR1", "EB_HALL", 33.0, w=1.4, kind="double_glazed", ang=0, axis="x", sign=False)
    P.door(L, "STAIR1", "C", 30.78, w=1.1, kind="double_glazed", ang=0, sign=False)
    for l in range(4):
        P.doors.append(Door(l, "L0.SHAFT", f"L{l}.C", LIFT_DOOR_X, w=LIFT_DOOR_W, kind="lift", h=LIFT_DOOR_H,
                            sign=False))
        if l > 0:
            P.door(l, "L0.STAIR1", "C", 30.78, w=1.1, kind="double_glazed", ang=0, sign=False)

    # --- west: catering block ---
    cat = dict(wall="tile_wall", floor="tile_floor")
    P.bay_room(L, FRONT, 0, 0, "Заготовочный цех", "Food preparation room", "food_prep", "D_catering", **cat)
    P.bay_room(L, FRONT, 1, 2, "Горячий цех (кухня)", "Kitchen (hot shop)", "kitchen", "D_catering",
               door_c=bay_cx(2), door_kw=dict(w=1.0, kind="metal_glazed"), **cat)
    P.door(L, "F0", "F1", 5.4, w=0.9, kind="std", axis="y", sign=False)
    P.bay_room(L, FRONT, 3, 3, "Раздаточная", "Food distribution counter", "distribution", "D_catering", **cat)
    P.door(L, "F1", "F3", 5.4, w=1.0, kind="std", axis="y", sign=False)
    P.bay_room(L, FRONT, 4, 6, "Обеденный зал", "Dining hall", "dining", "D_catering",
               door_c=18.0 + 1.6, door_kw=dict(w=1.4, kind="double_glazed", ang=0), wall="paint_peach",
               floor="linoleum_parquet")
    P.door(L, "F3", "F4", 3.2, w=2.4, kind="counter", sill=0.9, h=1.1, axis="y", sign=False)
    P.bay_room(L, FRONT, 7, 7, "Моечная столовой посуды", "Dishwashing room", "dishwash", "D_catering", **cat)
    P.door(L, "F7", "F4", 3.0, w=1.2, kind="counter", sill=0.9, h=1.0, axis="y", sign=False)
    o, i, cxo, cxi = split_L(FRONT, 8)
    P.room(L, "F8", "Бельевая (чистое бельё)", "Clean linen storage", o, "clean_linen", "E_technical", win=FRONT,
           wall="paint_blue")
    P.room(L, "F8i", "Грязное бельё", "Dirty linen collection", i, "dirty_linen", "E_technical", **cat)
    P.door(L, "F8", "C", cxo, w=0.8)
    P.door(L, "F8i", "C", cxi, w=0.8, kind="metal")
    o, i, cxo, cxi = split_L(REAR, 0)
    P.room(L, "R0", "Овощной цех", "Vegetable preparation room", o, "veg_prep", "D_catering", win=REAR, **cat)
    P.room(L, "R0i", "Камера пищевых отходов", "Waste collection room", i, "waste", "E_technical", **cat)
    P.door(L, "R0", "SC", cxo, w=0.8)
    P.door(L, "R0i", "SC", cxi, w=0.8, kind="metal")
    P.room(L, "STAIR2", "Лестница №2", "West staircase", [(3.06, 8.94, REAR_Y0, REAR_Y1)], "stair_end", "CIRC",
           numbered=False, z1=LEVELS[3] + CEIL_H, wall="paint_beige", floor="terrazzo")
    P.doors.append(Door(0, "L0.STAIR2", "EXT", REAR_EXITS[0], w=1.5, kind="steel_double", h=2.4,
                        ext=("y", REAR_Y1), sign=False))
    for l in range(4):
        P.doors.append(Door(l, "L0.STAIR2", f"L{l}.{'SC' if l == 0 else 'C'}", 3.78, w=1.1,
                            kind="double_glazed", sign=False))
    o, i = split_FB(REAR, 3)
    P.room(L, "R3", "Кладовая сухих продуктов", "Dry food storage", o, "dry_store", "D_catering", win=REAR,
           wall="paint_blue", floor="tile_floor")
    P.room(L, "R3i", "Охлаждаемая камера", "Refrigerated storage", i, "fridge", "D_catering", **cat)
    P.door(L, "R3i", "SC", bay_cx(3) - 0.6, w=0.9, kind="metal")
    P.door(L, "R3", "R3i", bay_cx(3) + 0.8, w=0.8, kind="std", axis="x", sign=False)
    o, i, cxo, cxi = split_L(REAR, 4)
    P.room(L, "R4", "Гардероб персонала пищеблока", "Kitchen staff changing room", o, "kitchen_changing",
           "D_catering", win=REAR, wall="paint_blue")
    P.room(L, "R4i", "Санузел персонала пищеблока", "Kitchen staff restroom", i, "staff_wc", "D_catering", **cat)
    P.door(L, "R4", "SC", cxo, w=0.8)
    P.door(L, "R4i", "SC", cxi, w=0.8, kind="wc_door")
    P.bay_room(L, REAR, 5, 5, "Столовая и комната отдыха персонала", "Staff dining room and staff room",
               "staff_dining", "D_catering", wall="paint_peach", floor="linoleum_parquet")
    o, i, cxo, cxi = split_L(REAR, 6)
    P.room(L, "R6", "Водомерный узел и тепловой пункт", "Water & plumbing service room", o, "plumbing",
           "E_technical", win=REAR, wall="plaster", floor="concrete")
    P.room(L, "R6i", "Электрощитовая", "Electrical distribution room", i, "electrical", "E_technical",
           wall="plaster", floor="concrete")
    P.door(L, "R6", "C", cxo, w=0.8, kind="metal")
    P.door(L, "R6i", "C", cxi, w=0.8, kind="metal")
    P.bay_room(L, REAR, 7, 7, "Венткамера", "Ventilation equipment room", "ventilation", "E_technical",
               door_kw=dict(kind="metal"), wall="plaster", floor="concrete")
    o, i, cxo, cxi = split_L(REAR, 8)
    P.room(L, "R8", "Мастерская", "Maintenance workshop", o, "workshop", "E_technical", win=REAR,
           wall="plaster", floor="concrete")
    P.room(L, "R8i", "Кладовая хозяйственная", "General storage room", i, "storage", "E_technical",
           wall="plaster", floor="concrete")
    P.door(L, "R8", "C", cxo, w=0.8)
    P.door(L, "R8i", "C", cxi, w=0.8)

    # --- east front: 2 offices + treatment-resort (spa) department ---
    P.bay_room(L, FRONT, 13, 13, "Главный врач", "Chief physician (director)", "director", "B_admin",
               door_kw=dict(kind="padded"), wall="wallpaper_b", floor="linoleum_parquet")
    P.bay_room(L, FRONT, 14, 14, "Администрация и бухгалтерия", "Administration and accounts", "admin_office",
               "B_admin", door_kw=dict(kind="glazed"), wall="wallpaper_a", floor="linoleum_parquet")
    spa = dict(dept="S_spa")
    P.bay_room(L, FRONT, 15, 16, "Массажный кабинет", "Massage room", "massage", door_c=bay_cx(15, 16),
               door_kw=dict(w=1.0, kind="wide"), wall="paint_peach", floor="linoleum_parquet", **spa)
    P.bay_room(L, FRONT, 17, 18, "Кабинет физиотерапии", "Physiotherapy room", "physio", door_c=bay_cx(17, 18),
               door_kw=dict(w=1.0, kind="wide"), wall="paint_blue", floor="linoleum_brown", **spa)
    P.bay_room(L, FRONT, 19, 20, "Ингаляторий и соляная комната", "Inhalation and salt room", "salt_room",
               door_c=bay_cx(19, 20), door_kw=dict(w=1.0, kind="wide"), wall="salt_brick",
               floor="linoleum_parquet", **spa)
    P.bay_room(L, FRONT, 21, 22, "Водолечебница (лечебные ванны и души)", "Hydrotherapy (baths and showers)",
               "hydro", door_c=bay_cx(21, 22), door_kw=dict(w=1.3, kind="double"), wall="tile_wall",
               floor="tile_floor", **spa)
    P.bay_room(L, FRONT, 23, 24, "Зал лечебной физкультуры (ЛФК)", "Therapeutic exercise hall", "lfk",
               door_c=bay_cx(23, 24), door_kw=dict(w=1.3, kind="double"), wall="paint_peach",
               floor="linoleum_parquet", **spa)

    # --- east rear: public WCs + medical department ---
    wc = dict(wall="tile_wall", floor="tile_floor")
    P.bay_room(L, REAR, 9, 9, "Туалет мужской", "Public men's restroom", "wc_men", "A_entrance",
               door_kw=dict(w=1.0, kind="wc_door"), **wc)
    P.bay_room(L, REAR, 10, 10, "Туалет женский", "Public women's restroom", "wc_women", "A_entrance",
               door_kw=dict(w=1.0, kind="wc_door"), **wc)
    o, i, cxo, cxi = split_L(REAR, 11)
    P.room(L, "R11", "Комната уборщиц", "Janitor's room", o, "janitor", "E_technical", win=REAR, wall="paint_blue")
    P.room(L, "R11i", "Кладовая уборочного инвентаря", "Cleaning equipment storage", i, "cleaning_store",
           "A_entrance", **wc)
    P.door(L, "R11", "C", cxo, w=0.8)
    P.door(L, "R11i", "C", cxi, w=0.8)
    o, i = split_FB(REAR, 12)
    P.room(L, "R12", "Медицинская регистратура", "Medical registration office", i, "med_reg", "C_medical",
           wall="paint_blue", floor="linoleum_parquet")
    P.room(L, "R12o", "Медицинский архив (картотека)", "Medical archive", o, "med_archive", "C_medical",
           win=REAR, wall="plaster", floor="linoleum_brown")
    P.door(L, "R12", "C", bay_cx(12) + 0.6, w=0.9, kind="glazed")
    P.door(L, "R12", "C", bay_cx(12) - 0.75, w=1.0, kind="counter", sill=0.95, h=1.0, sign=False)
    P.door(L, "R12o", "R12", bay_cx(12) - 0.7, w=0.8, kind="std", axis="x", sign=False)
    med = dict(dept="C_medical", wall="paint_blue", floor="linoleum_brown")
    P.bay_room(L, REAR, 13, 13, "Кабинет терапевта", "General practitioner's office", "gp",
               door_kw=dict(kind="glazed"), **med)
    P.bay_room(L, REAR, 14, 14, "Смотровой кабинет", "Medical examination room", "exam", **med)
    P.door(L, "R13", "R14", 13.2, w=0.8, axis="y", sign=False, swing="b")
    P.bay_room(L, REAR, 15, 15, "Кабинет врача-консультанта", "Doctor's consultation room", "consult", **med)
    P.bay_room(L, REAR, 16, 16, "Кабинет медицинских сестёр", "Nurses' office (head nurse)", "nurse_office", **med)
    P.bay_room(L, REAR, 17, 17, "Процедурный кабинет", "Treatment and injection room", "treatment",
               dept="C_medical", **wc)
    o, i = split_FB(REAR, 18)
    P.room(L, "R18", "Кабинет забора крови", "Blood sampling room", i, "blood", "C_medical", **wc)
    P.room(L, "R18o", "Клиническая лаборатория", "Small laboratory", o, "lab", "C_medical", win=REAR, **wc)
    P.door(L, "R18", "C", bay_cx(18), w=0.9)
    P.door(L, "R18o", "R18", bay_cx(18) - 0.7, w=0.8, axis="x", sign=False)
    P.bay_room(L, REAR, 19, 19, "Медпункт (первая помощь)", "First aid room", "first_aid", "C_medical",
               door_kw=dict(w=1.0, kind="wide"), wall="paint_blue", floor="tile_floor")
    o, i, cxo, cxi = split_L(REAR, 20)
    P.room(L, "R20", "Склад медицинского оборудования", "Medical equipment storage", o, "med_equip",
           "C_medical", win=REAR, wall="plaster")
    P.room(L, "R20i", "Склад медикаментов", "Medical supplies storage", i, "med_supplies", "C_medical",
           wall="paint_blue")
    P.door(L, "R20", "C", cxo, w=0.8, kind="metal")
    P.door(L, "R20i", "C", cxi, w=0.8, kind="metal")
    o, i, cxo, cxi = split_L(REAR, 21)
    P.room(L, "R21", "Гардероб медперсонала", "Medical staff changing room", o, "med_changing", "C_medical",
           win=REAR, wall="paint_blue")
    P.room(L, "R21i", "Санузел медперсонала", "Medical staff restroom", i, "staff_wc", "C_medical", **wc)
    P.door(L, "R21", "C", cxo, w=0.8)
    P.door(L, "R21i", "C", cxi, w=0.8, kind="wc_door")
    P.room(L, "STAIR3", "Лестница №3", "East staircase", [(66.06, 71.94, REAR_Y0, REAR_Y1)], "stair_end",
           "CIRC", numbered=False, z1=LEVELS[3] + CEIL_H, wall="paint_beige", floor="terrazzo")
    P.doors.append(Door(0, "L0.STAIR3", "EXT", REAR_EXITS[1], w=1.5, kind="steel_double", h=2.4,
                        ext=("y", REAR_Y1), sign=False))
    for l in range(4):
        P.doors.append(Door(l, "L0.STAIR3", f"L{l}.C", 71.22, w=1.1, kind="double_glazed", sign=False))
    o, i, cxo, cxi = split_L(REAR, 24)
    P.room(L, "R24", "Гардероб персонала", "Staff changing room", o, "staff_changing", "E_technical",
           win=REAR, wall="paint_blue")
    P.room(L, "R24i", "Хозяйственная (уборочная)", "Utility room", i, "utility", "E_technical", **wc)
    P.door(L, "R24", "C", cxo, w=0.8)
    P.door(L, "R24i", "C", cxi, w=0.8, kind="metal")

    # ======================= UPPER FLOORS (levels 1..3) ======================
    for L in (1, 2, 3):
        patient_floor(P, L)

    # club hall (entrance block, double height, level 1)
    P.room(1, "EB_HALL", "Клубный зал", "Club hall", [(ENT_IX0, ENT_IX1, ENT_IY0, -0.06)], "club_hall",
           "P_patient", z1=HALL_CEIL, wall="paint_peach", floor="linoleum_parquet", upper_wall="plaster",
           win="south")
    P.door(1, "F9", "EB_HALL", 28.5, w=1.4, kind="double_glazed", axis="x", ang=0)
    P.door(1, "L0.STAIR1", "EB_HALL", 33.0, w=1.4, kind="double_glazed", axis="x", ang=0, sign=False)
    P.door(1, "F12", "EB_HALL", 37.5, w=0.9, kind="std", axis="x")
    P.door(2, "L0.STAIR1", "L1.EB_HALL", 33.0, w=2.0, kind="window", sill=0.9, h=1.4, axis="x", sign=False)
    for x in (28.0, 29.0):
        P.door(2, "F9", "L1.EB_HALL", x, w=0.32, kind="port", sill=1.15, h=0.26, axis="x", sign=False)
    renumber(P)
    return P


def renumber(P):
    """Sequential room numbers per floor: entrance block from the entrance inwards, then the
    main wing from west to east (front before rear within a bay)."""
    for lvl in range(4):
        rs = [r for r in P.rooms.values() if r.level == lvl and r.num]

        def key(r):
            x0, x1, y0, y1 = r.bbox
            if y1 <= 0.01:      # entrance block
                return (0, (y0 + y1) / 2, 0)
            return (1, round((x0 + x1) / 2, 1), 0 if y0 < CORR_Y0 else 1)
        for i, r in enumerate(sorted(rs, key=key)):
            r.num = f"{lvl + 1}{i + 1:02d}"


ROOM_WALLS = ["wallpaper_a", "paint_peach", "wallpaper_b", "paint_beige"]


def patient_floor(P, L):
    pf = dict(dept="P_patient")
    corr_wall = {1: "paint_peach", 2: "paint_beige", 3: "paint_peach"}[L]
    P.room(L, "C", f"Коридор {L + 1}-го этажа", f"Floor {L + 1} corridor", [(MAIN_X0, MAIN_X1, CORR_Y0, CORR_Y1)],
           "corridor_patient", "CIRC", numbered=False, wall=corr_wall, floor="linoleum_brown")
    cnt = [0]

    def style():
        cnt[0] += 1
        return dict(wall=ROOM_WALLS[(cnt[0] + L) % len(ROOM_WALLS)],
                    floor="linoleum_parquet" if (cnt[0] + L) % 3 else "linoleum_brown")

    def double(side, k0, assisted=False):
        key = f"{SIDE_KEY[side]}{k0}"
        if assisted:
            room, bath, dc, bc = suite_rects(side, k0, k0 + 1, bw=2.2, bd=2.78)
            P.room(L, key, "Номер для маломобильных отдыхающих (2 места)", "Assisted-care room (2 beds)", room,
                   "suite_assisted", "P_patient", win=side, wall="paint_peach", floor="linoleum_parquet")
            P.room(L, key + "b", "Санузел номера (доступный)", "Accessible en-suite bathroom", [bath],
                   "suite_bath_access", "P_patient", numbered=False, wall="tile_wall", floor="tile_floor")
            P.door(L, key, "C", dc + 0.2, w=1.1, kind="wide")
            P.door(L, key + "b", key, bc, w=0.9, kind="wide", axis="y", sign=False, swing="b")
        else:
            room, bath, dc, bc = suite_rects(side, k0, k0 + 1)
            P.room(L, key, "Номер двухместный", "Double room with bathroom", room, "suite_double", "P_patient",
                   win=side, **style())
            P.room(L, key + "b", "Санузел номера", "En-suite bathroom", [bath], "suite_bath", "P_patient",
                   numbered=False, wall="tile_wall", floor="tile_floor")
            P.door(L, key, "C", dc, w=0.9)
            P.door(L, key + "b", key, bc, w=0.8, kind="wc_door", axis="y", sign=False, swing="b")

    def single(side, k):
        key = f"{SIDE_KEY[side]}{k}"
        o, i, cxo, cxi = split_L(side, k)
        P.room(L, key, "Номер одноместный", "Single room with bathroom", o, "suite_single", "P_patient", win=side,
               **style())
        P.room(L, key + "b", "Санузел номера", "En-suite bathroom", i, "suite_bath", "P_patient", numbered=False,
               wall="tile_wall", floor="tile_floor")
        P.door(L, key, "C", cxo, w=0.9)
        y0, y1 = i[0][2], i[0][3]
        P.door(L, key + "b", key, (y0 + y1) / 2, w=0.7, kind="wc_door", axis="y", sign=False, swing="b")

    # ---- front side ----
    for k in (0, 2, 4, 6):
        double(FRONT, k)
    single(FRONT, 8)
    if L == 1:
        P.room(L, "F9", "Фойе клубного зала", "Club hall foyer", [(27.06, 29.94, FRONT_Y0, CORR_Y0)], "foyer",
               "P_patient", numbered=False, wall="paint_peach", floor="linoleum_parquet")
        P.room(L, "F12", "Кладовая клубного зала", "Club hall storeroom", [(36.06, 38.94, FRONT_Y0, 3.5)],
               "hall_store", "P_patient", wall="plaster", floor="linoleum_brown")
        double(FRONT, 13, assisted=True)
        double(FRONT, 15, assisted=True)
    else:
        if L == 2:
            P.bay_room(L, FRONT, 9, 9, "Кинопроекционная", "Projection booth (club hall)", "projection",
                       "P_patient", door_kw=dict(kind="metal"), wall="plaster", floor="linoleum_brown")
        else:
            P.bay_room(L, FRONT, 9, 9, "Библиотека и читальня", "Library and reading room", "library",
                       "P_patient", wall="wallpaper_b", floor="linoleum_parquet")
        P.room(L, "F13", "Ординаторская", "Doctors' and staff office", [slot(FRONT, 13), (36.06, 39.06, FRONT_Y0, 3.5)],
               "staff_office", "P_patient", win=FRONT, wall="paint_blue", floor="linoleum_parquet")
        P.door(L, "F13", "C", bay_cx(13), w=0.9, kind="glazed")
        single(FRONT, 14)
        double(FRONT, 15)
    for k in (17, 19, 21, 23):
        double(FRONT, k)

    # ---- rear side ----
    single(REAR, 0)
    double(REAR, 3)
    for k, g in ((5, "m"), (6, "f")):
        ru = "Санузел и душевая мужские" if g == "m" else "Санузел и душевая женские"
        en = "Shared bathroom, men (WC + showers)" if g == "m" else "Shared bathroom, women (WC + showers)"
        P.bay_room(L, REAR, k, k, ru, en, f"wc_shower_{g}", "P_patient", door_kw=dict(w=1.0, kind="wc_door"),
                   wall="tile_wall", floor="tile_floor")
    P.bay_room(L, REAR, 7, 8, "Холл отдыха", "Lounge (TV, games, library corner)", "lounge", "P_patient",
               door_c=bay_cx(7, 8), door_kw=dict(w=1.4, kind="double_glazed", ang=0), wall="wallpaper_b",
               floor="linoleum_parquet")
    x0, x1, _, _ = slot(REAR, 9)
    P.room(L, "R9", "Пост дежурной медсестры", "Nursing station", [(x0, x1, CORR_Y1, REAR_Y0 + INNER_D)],
           "nurse_post", "P_patient", numbered=False, wall="paint_blue", floor="linoleum_brown")
    P.room(L, "R9o", "Кабинет медсестры", "Nurse's office", [(x0, x1, REAR_Y0 + INNER_D + PART_T, REAR_Y1)],
           "nurse_office_floor", "P_patient", win=REAR, wall="paint_blue", floor="linoleum_brown")
    P.door(L, "R9o", "R9", bay_cx(9) + 0.7, w=0.8, kind="glazed", axis="x")
    P.bay_room(L, REAR, 10, 10, "Процедурный кабинет", "Treatment room", "treatment_small", "P_patient",
               wall="tile_wall", floor="tile_floor")
    o, i = split_FB(REAR, 11)
    P.room(L, "R11", "Комната сестры-хозяйки", "Housekeeping room", i, "housekeeping", "P_patient",
           wall="paint_blue", floor="linoleum_brown")
    P.room(L, "R11o", "Бельевая (чистое бельё)", "Clean linen storage", o, "clean_linen", "P_patient",
           win=REAR, wall="paint_blue", floor="linoleum_brown")
    P.door(L, "R11", "C", bay_cx(11), w=0.9)
    P.door(L, "R11o", "R11", bay_cx(11) - 0.7, w=0.8, axis="x")
    P.bay_room(L, REAR, 12, 12, "Санузел для маломобильных", "Accessible bathroom", "access_bath", "P_patient",
               door_kw=dict(w=1.0, kind="wide"), wall="tile_wall", floor="tile_floor")
    o, i, cxo, cxi = split_L(REAR, 13)
    if L == 1:
        P.room(L, "R13", "Дежурный врач", "Doctor on duty", o, "doctor_duty", "P_patient", win=REAR,
               wall="paint_blue", floor="linoleum_parquet")
    else:
        P.room(L, "R13", "Медицинская кладовая", "Medical storage", o, "med_storage", "P_patient", win=REAR,
               wall="paint_blue", floor="linoleum_brown")
    P.room(L, "R13i", "Комната грязного белья", "Dirty linen collection", i, "dirty_linen", "P_patient",
           wall="tile_wall", floor="tile_floor")
    P.door(L, "R13", "C", cxo, w=0.8)
    P.door(L, "R13i", "C", cxi, w=0.8, kind="metal")
    for k in (14, 16, 18, 20):
        double(REAR, k)
    o, i, cxo, cxi = split_L(REAR, 24)
    P.room(L, "R24", "Хозяйственная кладовая", "Utility room", o, "utility", "P_patient", win=REAR,
           wall="paint_blue", floor="linoleum_brown")
    P.room(L, "R24i", "Кладовая уборочного инвентаря", "Cleaning equipment storage", i, "cleaning_store",
           "P_patient", wall="tile_wall", floor="tile_floor")
    P.door(L, "R24", "C", cxo, w=0.8)
    P.door(L, "R24i", "C", cxi, w=0.8)
