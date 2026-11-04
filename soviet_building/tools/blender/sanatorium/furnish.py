"""Furnishing recipes per room kind. Each recipe places period furniture and a few signs of
neglect that have a reason to be there (papers left on desks, a chair pushed over, an empty
medicine shelf, a cleaning cart left in a corridor)."""
import math
import random
from .params import *
from .furnish_core import Ctx, place_radiators_and_curtains
from .stairs_layout import stair_frame, CELL_U, CELL_V
from . import furniture as F

R = {}


def recipe(*kinds):
    def deco(fn):
        for k in kinds:
            R[k] = fn
        return fn
    return deco


def first(c, tries):
    for t in tries:
        ob = t()
        if ob is not None:
            return ob
    return None


def on_top(c, base_u, base_v, key, du, dv, z, facing="+v"):
    return c.at(key, base_u + du, base_v + dv, facing, z=z, check=False)


def decor_wall(c, keys, z=1.45, sides=("L", "R", "B")):
    """Hang items on walls at spread positions, skipping door/window zones."""
    for i, k in enumerate(keys):
        side = sides[i % len(sides)]
        span = c.W if side in ("W", "B") else c.D
        for t in (0.5, 0.3, 0.7, 0.2, 0.8):
            if c.hang(side, span * t, k, z):
                break


def switch(c):
    first(c, [lambda: c.hang("B", c.W - 0.35, "light_switch", 1.25), lambda: c.hang("B", 0.35, "light_switch", 1.25),
              lambda: c.hang("R", c.D - 0.4, "light_switch", 1.25)])
    first(c, [lambda: c.hang("L", c.D * 0.5, "socket", 0.3), lambda: c.hang("R", c.D * 0.5, "socket", 0.3)])


def floor_wear(c, n=1):
    for _ in range(n):
        if c.rng.random() < 0.6:
            c.at("stain" if c.rng.random() < 0.5 else "dust", c.rng.uniform(0.6, c.W - 0.6), c.rng.uniform(1.0, c.D - 1.0),
                 "+v", z=0.0, check=False)


def chair_maybe_tipped(c, key, u, v, facing):
    if c.rng.random() < 0.12:
        return c.at(key, u, v, facing, z=0.21, tilt=(math.pi / 2, 0))
    return c.at(key, u, v, facing)


# =============================================================== patient rooms
@recipe("patient_single")
def patient_single(c):
    left = c.rng.random() < 0.5
    bu = 0.52 if left else c.W - 0.52
    style = c.rng.choice(["bed", "bed", "bed_linen", "bed_bare"])
    c.at(style, bu, 2.1, "-v")
    c.at("bedside", bu + (0.75 if left else -0.75), 2.9, "-v")
    on_top(c, bu + (0.75 if left else -0.75), 2.9, "table_lamp", 0.05, 0, 0.62)
    du = c.W - 0.55 if left else 0.55
    c.at("desk_small", c.W / 2, 0.55, "+v") or c.at("desk_small", du, 1.4, "+u" if not left else "-u")
    first(c, [lambda: c.at("chair", c.W / 2 + 0.2, 1.05, "-v"), lambda: c.at("chair", du, 2.2, "-v")])
    first(c, [lambda: c.wall("R" if left else "L", 4.4, "wardrobe"), lambda: c.wall("R" if left else "L", 3.6, "wardrobe")])
    first(c, [lambda: c.wall("L" if left else "R", 5.3, "sink"), lambda: c.wall("R" if left else "L", 5.4, "sink")])
    first(c, [lambda: c.at("armchair", c.W - 0.45 if left else 0.45, 1.3, "+u" if left else "-u")])
    decor_wall(c, [c.rng.choice(["painting_1", "painting_2", "wall_carpet" if c.rng.random() < 0.3 else "painting_1"])],
               1.25, ("L" if left else "R",))
    if c.rng.random() < 0.35:
        first(c, [lambda: c.hang("B", 0.4, "radio", 1.9), lambda: c.hang("B", c.W - 0.4, "radio", 1.9)])
    switch(c)
    floor_wear(c)


@recipe("patient_double")
def patient_double(c):
    st = c.rng.choice(["bed", "bed_linen", "bed", "bed_bare"])
    c.at(st, 0.52, 2.1, "-v")
    c.at("bedside", 1.25, 2.9, "-v")
    c.at(st if c.rng.random() < 0.7 else "bed_bare", c.W - 0.52, 2.1, "-v")
    c.at("bedside", c.W - 0.27, 3.36, "-v")
    c.at("table_small", c.W / 2, 0.75, "+v")
    for du in (-0.45, 0.45):
        if c.rng.random() < 0.8:
            chair_maybe_tipped(c, "chair", c.W / 2 + du, 0.75 + (0.1 if du > 0 else -0.1), "+u" if du < 0 else "-u")
    on_top(c, c.W / 2, 0.75, "paper_stack", 0.05, 0.0, 0.72)
    first(c, [lambda: c.wall("R", 4.3, "wardrobe"), lambda: c.wall("L", 4.3, "wardrobe")])
    first(c, [lambda: c.wall("L", 5.25, "sink"), lambda: c.wall("R", 5.4, "sink"), lambda: c.wall("L", 4.4, "sink")])
    decor_wall(c, [c.rng.choice(["painting_1", "painting_2"])], 1.3, ("L",))
    if c.rng.random() < 0.35:
        decor_wall(c, ["wall_carpet"], 0.75, ("R",))
    if c.rng.random() < 0.35:
        first(c, [lambda: c.hang("B", 0.4, "radio", 1.9), lambda: c.hang("B", c.W - 0.4, "radio", 1.9)])
    switch(c)
    floor_wear(c)


@recipe("patient_assisted")
def patient_assisted(c):
    for u in (0.7, c.W - 0.7):
        c.at("bed_hospital", u, 2.0, "+v" if False else "-v")
        c.at("bedside", u + (0.75 if u < c.W / 2 else -0.75), 1.2, "-v")
    c.at("wheelchair", c.W / 2, 4.2, "+u")
    c.at("iv_stand", c.W / 2 - 0.5, 2.9, "+v")
    c.at("table_small", c.W / 2, 0.75, "+v")
    c.at("chair", c.W / 2 + 0.5, 0.8, "-u")
    first(c, [lambda: c.wall("R", 4.5, "wardrobe_wide"), lambda: c.wall("L", 5.2, "wardrobe")])
    decor_wall(c, ["painting_2", "schedule"], 1.35, ("L", "R"))
    switch(c)


@recipe("assisted_bath", "access_bath")
def access_bath(c):
    c.wall("L", c.D * 0.35, "toilet")
    c.hang("L", c.D * 0.35 + 0.45, "grab_bar", 0.8)
    c.hang("W" if c.room.kind == "access_bath" else "B", c.W * 0.3, "grab_bar", 0.8)
    first(c, [lambda: c.wall("R", c.D * 0.3, "sink"), lambda: c.wall("W", c.W - 0.4, "sink")])
    if c.room.kind == "access_bath":
        c.wall("R", c.D * 0.62, "bathtub")
        c.at("shower", 0.55, c.D * 0.62, "+u")
        c.hang("B", 0.4, "wc_access", 1.6) or None
        c.at("wheelchair", c.W * 0.6, c.D * 0.85, "-v")
    else:
        c.at("shower", c.W - 0.5, c.D - 0.6, "-v")
    floor_wear(c)


# ================================================================== circulation
@recipe("corridor", "corridor_patient", "service_corridor")
def corridor(c):
    """Wall-mounted equipment only, plus a few benches in pilaster bays: the 2.8 m corridor stays clear."""
    lvl = c.room.level
    W = c.W
    for i, t in enumerate([x for x in (5.0, 21.0, 39.5, 57.0, 69.0) if x < W - 1]):
        side = "W" if i % 2 else "B"
        first(c, [lambda: c.hang(side, t, "fire_ext", 0.0), lambda: c.hang(side, t + 1.2, "fire_ext", 0.0)])
        first(c, [lambda: c.hang(side, t + 2.0, "fire_sign", 1.75), lambda: c.hang(side, t + 1.6, "fire_sign", 1.75)])
    for t in (13.5, 46.5, 64.5):
        if t < W - 1:
            first(c, [lambda: c.hang("B", t, "hose_cabinet", 1.0), lambda: c.hang("W", t, "hose_cabinet", 1.0)])
    if c.room.kind != "service_corridor":
        for t in (27.0, 51.0):
            first(c, [lambda: c.hang("W", t, "bench", 0.0), lambda: c.hang("B", t + 3, "bench", 0.0)])
        first(c, [lambda: c.hang("W", 33.6 - c.O[0], "notice_board", 1.2), lambda: c.hang("B", 25.5 - c.O[0], "notice_board", 1.2)])
        first(c, [lambda: c.hang("B", 35.2 - c.O[0], "evac_plan", 1.4), lambda: c.hang("W", 32.0 - c.O[0], "evac_plan", 1.4)])
        first(c, [lambda: c.hang("W", 37.5 - c.O[0], "clock", 2.35), lambda: c.hang("B", 33.5 - c.O[0], "clock", 2.35)])
        for t, k in ((10.5, "arrow_stairs"), (60.0, "arrow_stairs"), (40.5, "arrow_lift")):
            first(c, [lambda: c.hang("W", t - c.O[0], k, 2.15), lambda: c.hang("B", t - c.O[0], k, 2.15)])
        if lvl == 0:
            for t, k in ((45.0, "arrow_medical"), (52.0, "arrow_admin"), (20.0, "arrow_dining"), (31.5, "arrow_reception")):
                first(c, [lambda: c.hang("W", t - c.O[0], k, 2.15), lambda: c.hang("B", t - c.O[0], k, 2.15)])
            first(c, [lambda: c.hang("W", 56.5 - c.O[0], "silence", 1.9)])
            first(c, [lambda: c.hang("B", 45.5 - c.O[0], "poster_4", 1.2), lambda: c.hang("W", 47.5 - c.O[0], "poster_4", 1.2)])
            first(c, [lambda: c.hang("W", 59.5 - c.O[0], "poster_3", 1.2)])
            c.at("stretcher", 61.8 - c.O[0], 0.5, "+u")
        else:
            first(c, [lambda: c.hang("B", 18.0 - c.O[0], "poster_5", 1.2), lambda: c.hang("W", 16.5 - c.O[0], "poster_5", 1.2)])
            first(c, [lambda: c.hang("W", 49.5 - c.O[0], "poster_1", 1.2), lambda: c.hang("B", 52.5 - c.O[0], "poster_1", 1.2)])
            first(c, [lambda: c.hang("B", 28.5 - c.O[0], "wall_newspaper", 1.25), lambda: c.hang("W", 22.5 - c.O[0], "wall_newspaper", 1.25)])
            first(c, [lambda: c.hang("W", 8.5 - c.O[0], "no_smoking", 1.7)])
            if lvl == 1:
                c.at("wheelchair", 40.4 - c.O[0], 2.35, "-v")
            if lvl == 2:
                c.at("cleaning_cart", 19.5 - c.O[0], 0.4, "+u")
                c.at("bucket", 20.1 - c.O[0], 0.35, "+u")
            if lvl == 3:
                # roof access under the stair houses: steel ladder + padlocked hatch
                for (xh, yw) in ((33.0, "W"), (66.0, "B")):
                    t = xh - c.O[0]
                    c.hang(yw, t, "ladder", 0.0)
                    c.hang(yw, t + 0.7, "roof_hatch_sign", 1.8)
                    vv = 0.45 if yw == "W" else c.D - 0.45
                    c.at("hatch", t, vv, "+v", z=CEIL_H - 0.001, check=False)
        for t in (1.0, 2.2):
            c.at("plant_1" if t < 2 else "plant_2", 29.6 - c.O[0] + t * 0.0 + (0 if t < 2 else 8.5), 0.35, "+v")
    else:
        first(c, [lambda: c.hang("W", 2.5, "menu_board", 1.3)])
        c.at("crates", 13.0, 0.3, "+v")
    for k in range(3):
        if c.rng.random() < 0.5:
            c.at("papers_1" if k % 2 else "papers_2", c.rng.uniform(3, W - 3), c.rng.uniform(0.8, 2.0), "+v", z=0.0, check=False)
    floor_wear(c, 3)


@recipe("hall")
def hall(c):
    """Reception hall: wooden reception counter in front of the registration windows, info boards."""
    # The registration windows face this room; the counter shelf is built with the openings.
    c.at("seat_row", 32.5 - 30.12, 1.2, "+v")
    c.at("plant_1", 0.5, 0.6, "+v")
    c.at("plant_2", 4.4, 0.6, "+v")
    c.at("coat_stand", 0.5, 4.0, "+v")
    decor_wall(c, ["notice_board", "evac_plan", "poster_1", "schedule"], 1.3, ("L",))
    c.hang("L", 9.0, "arrow_medical", 2.15)
    c.hang("L", 10.5, "clock", 2.4)
    floor_wear(c, 3)


@recipe("waiting")
def waiting(c):
    for i, u in enumerate((1.4, 3.3, 5.2)):
        c.at("seat_row", u, 2.6, "-v")
        c.at("seat_row", u, 4.0, "+v")
    c.at("table_coffee", 6.8, 3.3, "+v")
    c.at("plant_1", 0.4, 0.4, "+v")
    c.at("plant_2", c.W - 0.4, 0.4, "+v")
    c.at("tv", c.W - 0.6, 3.3, "-u")
    on_top(c, 6.8, 3.3, "papers_2", 0, 0, 0.5)
    decor_wall(c, ["poster_2", "poster_6", "calendar", "painting_1"], 1.35, ("L", "R"))
    floor_wear(c, 2)


@recipe("vestibule")
def vestibule(c):
    c.at("runner", c.W / 2, 1.2, "+u", z=0.0, check=False)
    decor_wall(c, ["exit_sign"], 2.6, ("L",))


@recipe("foyer")
def foyer(c):
    c.wall("L", 2.5, "bench")
    c.wall("R", 4.0, "bench") if c.rng.random() < 2 else None
    c.at("plant_1", 0.4, 0.5, "+v")
    decor_wall(c, ["poster_5", "schedule", "arrow_hall"], 1.4, ("L", "R"))


# ================================================================ entrance block
@recipe("luggage")
def luggage(c):
    for t in (0.6, 1.8):
        c.wall("R", t, "goods_rack")
    c.wall("L", 1.8, "crates")
    c.at("sack", 1.6, 1.2, "+v")
    c.at("chair", 2.0, 0.6, "-v")


@recipe("coatroom")
def coatroom(c):
    for v in (1.0, 2.2):
        for u in (0.8, 2.1):
            c.at("coat_stand", u, v, "+v")
    c.at("chair", 0.6, 0.5, "+u")
    c.hang("R", 1.0, "schedule", 1.4)


@recipe("registration")
def registration(c):
    for t in (1.6, 3.6):
        c.wall("R", t, "desk_office")
        c.at("chair_tube", c.W - 1.15, t, "+u")
        on_top(c, c.W - 0.4, t, "telephone", 0, 0.3, 0.76)
        on_top(c, c.W - 0.4, t, "paper_stack", 0, -0.3, 0.76)
    for t in (0.6, 1.2, 1.8):
        c.wall("L", t, "filing")
    c.wall("L", 3.0, "binders")
    c.wall("L", 4.2, "binders")
    c.wall("W", 4.5, "safe")
    c.at("papers_1", 1.8, 2.5, "+v", z=0.0, check=False)
    decor_wall(c, ["calendar", "schedule"], 1.5, ("B",))


@recipe("info")
def info(c):
    c.wall("R", 1.5, "desk_office")
    c.at("chair_tube", c.W - 1.15, 1.6, "+u")
    on_top(c, c.W - 0.4, 1.5, "telephone", 0, 0.3, 0.76)
    on_top(c, c.W - 0.4, 1.5, "papers_1", 0, -0.2, 0.761)
    c.wall("L", 1.0, "binders")
    c.wall("L", 2.2, "filing")
    decor_wall(c, ["calendar"], 1.5, ("B",))


@recipe("guard")
def guard(c):
    c.wall("R", 1.2, "desk_office")
    c.at("chair_tube", c.W - 1.15, 1.2, "+u")
    on_top(c, c.W - 0.4, 1.2, "telephone", 0, 0.35, 0.76)
    c.wall("L", 0.7, "locker")
    c.wall("L", 1.3, "locker")
    c.wall("W", 2.6, "fuse_box", 1.2) if False else c.hang("B", 1.0, "fuse_box", 1.3)
    c.hang("L", 2.4, "clock", 2.0)
    c.at("bed_bare", c.W / 2 - 0.3, 2.6, "+u") if False else c.at("chair", 1.6, 2.4, "-u")
    decor_wall(c, ["calendar", "evac_plan"], 1.4, ("B", "L"))


# ======================================================================= catering
@recipe("kitchen")
def kitchen(c):
    for t in (1.0, 2.1, 3.2):
        c.wall("L", t, "stove")
    c.wall("R", 1.0, "kettle")
    c.wall("R", 2.0, "kettle")
    c.at("prep_table", c.W / 2 + 0.2, 4.2, "+u")
    c.wall("R", 3.4, "prep_table")
    c.wall("L", 4.8, "kitchen_sink")
    c.wall("R", 5.2, "dish_rack")
    c.at("duct", c.W / 2, 2.1, "+u", z=CEIL_H - 0.45, check=False)
    c.at("bucket", c.W / 2 + 1.2, 1.2, "+v")
    decor_wall(c, ["menu_board", "electro_warning"], 1.5, ("B",))
    floor_wear(c, 2)


@recipe("food_prep")
def food_prep(c):
    c.wall("R", 1.0, "prep_table")
    c.wall("R", 2.6, "prep_table")
    c.wall("L", 1.5, "kitchen_sink")
    c.wall("L", 3.2, "fridge_ind")
    c.at("bin", 1.4, 4.6, "+v")
    decor_wall(c, ["poster_2"], 1.4, ("L",))


@recipe("veg_prep")
def veg_prep(c):
    c.wall("L", 1.0, "kitchen_sink")
    c.at("peeler", c.W - 0.5, 1.0, "-u")
    c.wall("R", 2.3, "prep_table")
    c.at("crates", 0.5, 2.6, "+u")
    c.at("sack", 1.2, 2.8, "+v")


@recipe("distribution")
def distribution(c):
    c.wall("R", 3.2, "serving_line")
    c.wall("L", 1.5, "kettle")
    c.wall("L", 4.6, "dish_rack")
    c.at("prep_table", 1.3, 5.2, "+u") if False else None
    decor_wall(c, ["menu_board"], 1.5, ("B",))


@recipe("dining")
def dining(c):
    for i in range(3):
        for j in range(3):
            u, v = 1.5 + i * 3.0, 1.25 + j * 1.7
            c.at("table_dining", u, v, "+v")
            for du in (-0.32, 0.32):
                for dv, f in ((-0.62, "+v"), (0.62, "-v")):
                    if c.rng.random() < 0.85:
                        chair_maybe_tipped(c, "chair_tube", u + du, v + dv, f)
            if c.rng.random() < 0.3:
                on_top(c, u, v, "papers_1", 0, 0, 0.751)
    c.wall("B", 1.0, "plant_1")
    decor_wall(c, ["poster_6", "poster_2", "menu_board", "painting_2", "clock"], 1.5, ("L", "B", "R"))
    floor_wear(c, 3)


@recipe("dishwash")
def dishwash(c):
    c.wall("R", 1.3, "dishwasher")
    c.wall("L", 1.5, "kitchen_sink")
    c.wall("L", 3.0, "kitchen_sink")
    c.wall("R", 3.2, "dish_rack")
    c.at("bin", 1.4, 5.0, "+v")


@recipe("dry_store")
def dry_store(c):
    for t in (0.7, 2.0):
        c.wall("L", t, "goods_rack")
    c.wall("R", 1.2, "goods_rack")
    c.at("sack", 1.6, 2.2, "+v")
    c.at("sack", 1.0, 2.5, "+u")


@recipe("fridge")
def fridge(c):
    c.wall("L", 0.8, "fridge_ind")
    c.wall("R", 0.9, "goods_rack")
    c.at("crates", 1.5, 1.9, "+v")


@recipe("kitchen_changing", "staff_changing", "med_changing")
def changing(c):
    for t in (0.5, 1.05, 1.6, 2.15):
        c.wall("L", t, "locker")
    c.wall("R", 1.2, "bench")
    c.hang("R", 2.6, "mirror", 1.2)
    c.at("coat_stand", c.W - 0.4, 0.5, "+v") if c.D > 2.5 else None
    decor_wall(c, ["schedule"], 1.5, ("W",))


@recipe("kitchen_wc", "med_wc")
def small_wc(c):
    c.wall("B" if False else "W", c.W / 2, "toilet")
    c.wall("L", c.D - 0.6, "sink")


@recipe("staff_dining")
def staff_dining(c):
    for v in (1.4, 3.4):
        c.at("table_dining", c.W / 2, v, "+v")
        for du in (-0.32, 0.32):
            c.at("chair", c.W / 2 + du, v - 0.62, "+v")
            c.at("chair", c.W / 2 + du, v + 0.62, "-v")
    c.wall("L", 5.0, "fridge")
    decor_wall(c, ["calendar", "poster_6"], 1.4, ("R",))


# ===================================================================== technical
@recipe("plumbing")
def plumbing(c):
    c.at("pump", 0.9, 1.2, "+u")
    c.at("boiler", c.W - 0.6, 1.0, "-u")
    c.hang("L", 2.8, "elec_panel_wall", 1.2)
    c.at("bucket", 1.8, 2.6, "+v")


@recipe("electrical")
def electrical(c):
    c.wall("L", 0.8, "elec_cabinet")
    c.wall("L", 1.7, "elec_cabinet")
    c.hang("R", 1.3, "electro_warning", 1.6)
    c.hang("R", 0.8, "fuse_box", 1.2)


@recipe("ventilation")
def ventilation(c):
    c.at("pump", 1.0, 1.5, "+u")
    c.at("duct", c.W / 2, 3.0, "+u", z=CEIL_H - 0.5, check=False)
    c.wall("R", 3.5, "elec_cabinet")
    c.hang("L", 4.5, "vent_grille", 2.4)


@recipe("workshop")
def workshop(c):
    c.wall("L", 1.3, "workbench")
    c.wall("R", 1.0, "tool_rack")
    c.wall("R", 2.3, "goods_rack")
    c.at("chair", 1.3, 1.6, "-u")
    c.at("bucket", 2.2, 2.6, "+v")
    decor_wall(c, ["calendar", "electro_warning"], 1.5, ("L",))


@recipe("storage", "utility", "cleaning_store", "hall_store")
def storage(c):
    c.wall("L", min(0.8, c.D / 2), "goods_rack")
    if c.room.kind in ("utility", "cleaning_store"):
        c.at("bucket", c.W - 0.3, c.D * 0.6, "+v")
        c.at("cleaning_cart", c.W / 2, c.D * 0.3, "+u")
    if c.room.kind == "hall_store":
        for t in (1.8, 2.6):
            c.wall("R", t, "seat_row")
        c.at("chair", 1.2, 2.3, "+v")
        c.at("chair", 1.6, 2.3, "+v")


@recipe("waste")
def waste(c):
    c.at("bin", 0.4, 0.5, "+v")
    c.at("bin", 0.4, 1.2, "+v")
    c.at("bin", 0.4, 1.9, "+v")


@recipe("clean_linen")
def clean_linen(c):
    for t in (0.8, 2.2):
        c.wall("L", t, "linen_rack")
    c.wall("R", 1.0, "linen_rack")
    c.at("laundry_cart", c.W / 2, c.D - 0.8, "+u")


@recipe("dirty_linen")
def dirty_linen(c):
    c.at("laundry_cart", c.W / 2, 1.0, "+v")
    c.at("bin", c.W / 2, 2.0, "+v")


@recipe("janitor")
def janitor(c):
    c.wall("L", 0.8, "locker")
    c.wall("L", 1.35, "locker")
    c.at("table_small", c.W - 0.5, 0.7, "+v")
    c.at("chair", c.W - 1.0, 0.8, "+u")
    c.at("cleaning_cart", 1.0, 2.6, "+u")
    c.wall("R", 2.6, "kitchen_sink")


@recipe("machine_room")
def machine_room(c):
    c.hang("L", 2.5, "electro_warning", 1.6)
    c.hang("R", 2.6, "keep_out", 1.7)


# ===================================================================== offices
def office(c, desk="desk_office", boss=False, extra=()):
    du = c.W / 2
    c.at("runner" if boss else "rug", du, 3.0, "+v", z=0.0, check=False) if boss or c.rng.random() < 0.3 else None
    c.at(desk, du, 1.35, "+v")
    c.at("armchair" if boss else "chair_tube", du, 0.6, "+v")
    c.at("chair", du - 0.35, 2.05, "-v")
    if boss:
        c.at("chair", du + 0.35, 2.05, "-v")
    on_top(c, du, 1.35, "telephone", 0.45, 0.1, 0.76)
    on_top(c, du, 1.35, "paper_stack", -0.4, 0.05, 0.76)
    if c.rng.random() < 0.6:
        on_top(c, du, 1.35, "papers_2", 0.0, 0.05, 0.762)
    if "typewriter" in extra:
        on_top(c, du, 1.35, "typewriter", 0.05, -0.05, 0.76)
    c.wall("L", 3.2, "bookcase" if boss else "binders")
    c.wall("L", 4.3, "filing" if c.rng.random() < 0.5 else "bookcase")
    first(c, [lambda: c.wall("R", 3.4, "safe" if "safe" in extra else "filing"), lambda: c.wall("R", 2.6, "filing")])
    first(c, [lambda: c.wall("R", 4.6, "coat_stand"), lambda: c.wall("R", 5.2, "coat_stand")])
    if "meeting" in extra:
        c.at("table_sq", du, 3.6, "+v")
    decor_wall(c, ["calendar", "clock", c.rng.choice(["painting_1", "frame_photo", "poster_1"])], 1.55, ("L", "R", "B"))
    switch(c)
    if c.rng.random() < 0.5:
        c.at("papers_1", c.rng.uniform(0.6, c.W - 0.6), c.rng.uniform(2.5, 4.5), "+v", z=0.0, check=False)
    floor_wear(c)


@recipe("director")
def director(c):
    office(c, "desk_wide", boss=True, extra=("safe",))
    c.at("table_sq", c.W / 2, 3.4, "+v") if False else None
    c.at("armchair", c.W / 2 - 0.6, 4.3, "-u")
    c.wall("B", 0.5, "plant_1") if False else None


@recipe("secretary")
def secretary(c):
    office(c, extra=("typewriter",))
    c.at("seat_row", 1.0, 4.2, "+u") if False else None


@recipe("deputy", "chief_admin")
def deputy(c):
    office(c, "desk_office", boss=c.room.kind == "deputy")


@recipe("accountant")
def accountant(c):
    office(c, extra=("safe", "typewriter"))


@recipe("hr", "admin_office", "head_nurse", "staff_office", "doctor_duty")
def generic_office(c):
    office(c, extra=("typewriter",) if c.room.kind in ("hr", "admin_office") else ())
    if c.room.kind in ("doctor_duty",):
        c.wall("R", 5.0, "bed_bare") if False else c.at("sofa", c.W / 2, 5.0, "-v")


@recipe("meeting")
def meeting(c):
    c.at("meeting_table", c.W / 2, 2.8, "+u")
    for v in (1.9, 2.5, 3.1, 3.7):
        for u, f in ((c.W / 2 - 0.75, "+u"), (c.W / 2 + 0.75, "-u")):
            if c.rng.random() < 0.9:
                chair_maybe_tipped(c, "chair", u, v, f)
    c.at("chair", c.W / 2, 1.2, "+v")
    c.wall("L", 5.0, "bookcase")
    c.at("tv", c.W / 2, 5.0, "-v") if False else None
    decor_wall(c, ["notice_board", "clock", "poster_1"], 1.4, ("R", "B", "L"))


@recipe("staff_room")
def staff_room(c):
    c.at("sofa", c.W / 2, 4.2, "-v")
    c.at("table_coffee", c.W / 2, 3.2, "+v")
    c.at("armchair", 0.5, 2.5, "+u")
    c.at("table_small", c.W / 2, 1.0, "+v")
    c.at("chair", c.W / 2 - 0.45, 1.0, "+u")
    c.wall("R", 1.9, "fridge")
    on_top(c, c.W / 2, 1.0, "telephone", 0, 0, 0.72) if False else None
    decor_wall(c, ["calendar", "painting_2", "wall_newspaper"], 1.4, ("L", "R", "B"))
    switch(c)


@recipe("archive", "records", "med_archive", "med_supplies", "med_equip", "med_storage")
def archive(c):
    key = {"med_supplies": "medbox_rack", "med_equip": "goods_rack", "med_storage": "medbox_rack"}.get(c.room.kind, "binders")
    for t in (0.6, 1.7, 2.8):
        if t + 0.5 < c.D:
            c.wall("L", t, key)
    if c.W > 2.3:
        for t in (0.8, 2.0):
            if t + 0.5 < c.D:
                c.wall("R", t, key if c.room.kind != "med_equip" else "med_cabinet")
    if c.room.kind == "med_equip":
        c.at("oxygen", c.W / 2, 0.6, "+v")
        c.at("iv_stand", c.W / 2 + 0.3, 1.5, "+v")
    if c.room.kind in ("archive", "med_archive"):
        c.at("papers_2", c.W / 2, c.D * 0.5, "+v", z=0.0, check=False)


# ===================================================================== medical
def med_desk(c):
    du = c.W / 2
    c.wall("L", 1.0, "desk_office")
    c.at("chair_tube", 1.15, 1.0, "-u")
    c.at("chair", 1.4, 1.9, "-v")
    on_top(c, 0.4, 1.0, "paper_stack", 0, 0.2, 0.76)
    on_top(c, 0.4, 1.0, "table_lamp", 0, -0.45, 0.76)


@recipe("gp", "consult", "nurse_office", "nurse_office_floor")
def gp(c):
    med_desk(c)
    if c.room.kind in ("gp", "consult"):
        c.wall("R", 1.4, "exam_couch") if False else c.at("exam_couch", c.W - 0.4, 2.0, "-u")
        c.at("screen", c.W - 0.6, 3.4, "-v") if False else None
    c.wall("R", 3.6, "med_cabinet")
    first(c, [lambda: c.wall("L", 3.2, "sink"), lambda: c.wall("L", 4.6, "sink")])
    c.wall("L", 4.4, "filing") if c.D > 5 else None
    decor_wall(c, ["anatomy", "poster_4" if c.rng.random() < 0.5 else "poster_2", "calendar"], 1.45, ("R", "L", "B"))
    switch(c)


@recipe("exam")
def exam(c):
    c.at("exam_couch", c.W / 2, 2.2, "+v" if False else "-v")
    c.at("screen", c.W / 2, 3.6, "-v")
    c.wall("R", 1.0, "instrument_table")
    c.wall("L", 1.0, "scale")
    c.wall("R", 4.6, "med_cabinet")
    c.wall("L", 4.8, "sink")
    c.hang("L", 3.0, "eye_chart", 1.2)
    floor_wear(c)


@recipe("treatment", "treatment_small", "first_aid", "blood")
def treatment(c):
    if c.room.kind == "blood":
        c.at("armchair", c.W / 2, 1.6, "-v")
        c.wall("R", 1.6, "instrument_table")
        c.wall("L", 3.0, "fridge")
    else:
        c.at("exam_couch", c.W - 0.45, 2.2, "-u")
        c.wall("L", 1.2, "instrument_table")
        c.at("iv_stand", c.W - 1.1, 1.0, "+v")
    c.wall("L", 2.2, "med_cabinet")
    c.wall("R", 4.0, "med_cabinet")
    first(c, [lambda: c.wall("L", 4.8, "sink"), lambda: c.wall("L", 3.8, "sink")])
    c.at("chair_tube", c.W / 2, 3.2, "-v")
    if c.room.kind == "first_aid":
        c.at("stretcher", c.W / 2 - 0.2, 4.4, "+u")
        c.at("oxygen", 0.3, 0.6, "+v")
        c.at("wheelchair", c.W - 0.5, 5.2, "-v")
    decor_wall(c, ["poster_4", "schedule"], 1.5, ("R", "B"))


@recipe("lab")
def lab(c):
    c.wall("L", 1.2, "table_lab")
    c.wall("L", 2.8, "table_lab")
    on_top(c, 0.35, 1.2, "microscope", 0, 0.2, 0.85, "+u")
    on_top(c, 0.35, 2.8, "centrifuge", 0, 0.0, 0.85)
    c.wall("R", 1.3, "lab_rack")
    c.wall("R", 2.8, "med_cabinet")
    c.wall("R", 4.2, "fridge")
    c.at("chair_tube", 1.1, 1.3, "-u")
    first(c, [lambda: c.wall("L", 4.6, "sink")])
    decor_wall(c, ["schedule", "calendar"], 1.5, ("B",))


@recipe("med_reg")
def med_reg(c):
    c.wall("L", 0.9, "desk_office") if False else c.at("desk_office", 0.85, c.D - 0.6, "-v")
    c.at("chair_tube", 0.85, c.D - 1.2, "-v") if False else c.at("chair_tube", 0.85, 0.8, "-v")
    c.wall("R", 0.8, "filing")
    c.wall("R", 1.4, "filing")


# ================================================================ patient floors
@recipe("nurse_post")
def nurse_post(c):
    c.at("desk_wide", c.W / 2, 1.3, "+v")
    c.at("chair_tube", c.W / 2, 0.55, "+v")
    on_top(c, c.W / 2, 1.2, "telephone", 0.5, 0, 0.76)
    on_top(c, c.W / 2, 1.2, "table_lamp", -0.6, 0.1, 0.76)
    on_top(c, c.W / 2, 1.2, "paper_stack", 0, 0, 0.76)
    c.wall("L", 0.6, "med_cabinet") if False else c.wall("W", 0.5, "filing")
    decor_wall(c, ["schedule", "clock"], 1.6, ("W",))


@recipe("housekeeping")
def housekeeping(c):
    c.at("table_small", c.W / 2, 1.0, "+v")
    c.at("chair", c.W / 2 - 0.45, 1.0, "+u")
    c.wall("L", 1.8, "linen_rack")
    c.at("laundry_cart", c.W - 0.5, 1.8, "-u")


@recipe("wc_men", "wc_women", "wc_shower_m", "wc_shower_f")
def wc(c):
    men = c.room.kind in ("wc_men", "wc_shower_m")
    shower = c.room.kind.startswith("wc_shower")
    # sinks near the corridor end (lobby), cubicles along the left wall, accessible cubicle at the window end
    for t in (c.W * 0.3, c.W * 0.7):
        c.wall("B", t, "sink") if False else None
    for v in (4.6, 5.2):
        c.wall("R", v, "sink")
    n = 2 if shower else 3
    for k in range(n):
        v = 1.9 + k * 1.0
        c.at("cubicle", 0.72, v + 0.5, "+u", check=False)
        c.wall("L", v + 0.5, "toilet")
    if shower:
        c.at("shower", 0.5, 0.75, "+u")
        c.at("shower", c.W - 0.5, 0.75, "-u")
    else:
        c.wall("W", 0.6, "toilet")
        c.hang("L", 0.9, "grab_bar", 0.8)
    if men:
        for v in (2.2, 3.0):
            c.wall("R", v, "urinal")
    c.hang("R", 3.9, "mirror", 1.2)
    c.at("bucket", c.W - 0.4, 1.4, "+v")
    floor_wear(c, 2)


@recipe("lounge")
def lounge(c):
    c.at("tv", c.W / 2, 0.8, "+v")
    for u in (c.W / 2 - 1.2, c.W / 2, c.W / 2 + 1.2):
        c.at("armchair" if u != c.W / 2 else "sofa", u, 2.3, "-v")
    c.at("table_coffee", c.W / 2, 3.3, "+v")
    c.at("table_sq", 1.4, 4.6, "+v")
    for du in (-0.55, 0.55):
        c.at("chair", 1.4 + du, 4.6, "+u" if du < 0 else "-u")
    c.wall("R", 4.0, "books")
    c.at("plant_1", 0.4, 0.4, "+v")
    c.at("plant_2", c.W - 0.4, 0.4, "+v")
    c.at("rug", c.W / 2, 2.5, "+v", z=0.0, check=False)
    decor_wall(c, ["painting_1", "wall_newspaper", "schedule"], 1.4, ("L", "B", "R"))


@recipe("projection")
def projection(c):
    c.at("projector", 0.9, 0.9, "-v")
    c.at("projector", 1.9, 0.9, "-v")
    c.wall("L", 3.0, "goods_rack")
    c.at("chair", 1.4, 2.0, "-v")
    c.hang("R", 3.5, "keep_out", 1.6)


@recipe("club_hall")
def club_hall(c):
    """Club hall: stage with curtain at the south end, cinema rows, piano, TV corner, chess tables."""
    W, D = c.W, c.D
    c.at("stage", W / 2, 1.6, "+v", foot=(W, 3.2), check=False)
    c.at("stage_curtain", W / 2, 0.25, "+v", z=0.6, check=False)
    c.at("piano", 1.3, 3.8, "+u")
    for k in range(6):
        for u in (W / 2 - 2.68, W / 2 + 2.68):
            c.at("cinema_row", u, 5.4 + k * 1.0, "-v")
    c.at("tv", W - 0.6, 15.5, "-u")
    c.at("sofa", W - 2.3, 15.5, "+u")
    for (u, v) in ((2.0, 15.6), (2.0, 17.2)):
        c.at("table_sq", u, v, "+v")
        c.at("chair", u - 0.6, v, "+u")
        c.at("chair", u + 0.6, v, "-u")
    for v in (13.0, 17.6):
        c.at("plant_1", 0.4, v, "+u")
        c.at("plant_2", W - 0.4, v - 1.0, "-u")
    decor_wall(c, ["poster_5", "poster_1", "wall_newspaper", "painting_2"], 1.5, ("L", "R"))


@recipe("stair_main", "stair_end")
def stair(c):
    """Floor-level lobby beside the windows on every storey: bench and a plant (relaxation corner)."""
    r = c.room
    f = stair_frame(r)
    o, p1 = f(0, 0), f(0, -1)
    rot = math.atan2(p1[1] - o[1], p1[0] - o[0]) + math.pi / 2      # front towards local -v
    for i, L in enumerate(LEVELS):
        if r.kind == "stair_end" or i in (2, 3):
            x, y = f(3.6, CELL_V - 0.5)
            c.B.lib.place("bench", F.MODS["bench"][0], c.B.coll_for(r.rid), f"bench_{r.rid}_{i}", (x, y, L), rot,
                          c.B.room_empty[r.rid])
            c.B.stats["Furniture"] = c.B.stats.get("Furniture", 0) + c.B.lib.meshes["bench"][1]
        x2, y2 = f(CELL_U - 0.45, CELL_V - 0.45)
        c.B.lib.place("plant_1", F.MODS["plant_1"][0], c.B.coll_for(r.rid), f"plant_{r.rid}_{i}", (x2, y2, L), 0,
                      c.B.room_empty[r.rid])
        c.B.stats["Furniture"] = c.B.stats.get("Furniture", 0) + c.B.lib.meshes["plant_1"][1]


@recipe("shaft")
def none(c):
    pass


def furnish_all(B):
    place_radiators_and_curtains(B)
    missing = set()
    for r in B.plan.rooms.values():
        fn = R.get(r.kind)
        if fn is None:
            missing.add(r.kind)
            continue
        c = Ctx(B, r, random.Random(r.seed))
        fn(c)
    B.stats["recipes_missing"] = sorted(missing)
