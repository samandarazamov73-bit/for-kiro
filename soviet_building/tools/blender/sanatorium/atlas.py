"""Texture atlas layouts shared by the texture painter and the mesh UV mapping.

Regions are packed deterministically (shelf packer) from ordered (name, w, h) lists, so
texgen_atlas.py and the Blender build always agree on the rectangles."""

FURN_W, FURN_H = 4096, 2048
FURN = [
    # name, width px, height px   (4096 x 2048 px atlas)
    ("wood_plain", 512, 512), ("wardrobe_front", 256, 512), ("bookcase_front", 256, 512),
    ("filing_front", 256, 512), ("med_cabinet_front", 256, 512), ("fridge_front", 256, 512),
    ("elec_panel", 256, 512), ("elevator_door", 256, 512), ("cabin_wall", 256, 512),
    ("hose_cabinet", 256, 512), ("partition", 256, 512), ("stage_curtain", 256, 512),
    ("cabin_panel", 128, 512), ("landing_panel", 128, 512), ("door_steel", 256, 512),
    ("door_glazed", 256, 512), ("door_padded", 256, 512),
    ("desk_front", 512, 256), ("radiator", 512, 256), ("cinema_seats", 512, 256),
    ("bedside_front", 256, 256), ("safe_front", 256, 256), ("stove_top", 256, 256), ("stove_front", 256, 256),
    ("steel", 256, 256), ("fuse_board", 256, 256), ("vent_unit", 256, 256), ("pump", 256, 256),
    ("mattress", 256, 256), ("blanket", 256, 256), ("linen_white", 256, 256), ("upholstery_brown", 256, 256),
    ("upholstery_green", 256, 256), ("typewriter_top", 256, 256), ("tv_front", 256, 256),
    ("piano_front", 256, 256), ("book_spines", 256, 256), ("binders", 256, 256), ("linen_stack", 256, 256),
    ("crates", 256, 256), ("sacks", 256, 256), ("tools_board", 256, 256), ("screen_fabric", 256, 256),
    ("lift_machine", 256, 256), ("clock_face", 256, 256), ("dish_rack", 256, 256), ("shelf_goods", 256, 256),
    ("lab_equipment", 256, 256), ("med_boxes", 256, 256), ("carpet_rug", 256, 256), ("runner", 256, 256),
    ("floor_indicator", 256, 128), ("exam_couch", 256, 128), ("drawer_front", 256, 128),
    ("fluo_diffuser", 256, 128), ("telephone", 128, 128), ("paper_stack", 128, 128), ("pillow", 128, 128),
    ("metal_white", 128, 128), ("metal_cream", 128, 128), ("metal_green", 128, 128), ("metal_grey", 128, 128),
    ("black_plastic", 128, 128), ("chrome", 128, 128), ("porcelain", 128, 128), ("mirror", 128, 128),
    ("lamp_shade", 128, 128), ("plafond", 128, 128), ("rubber_black", 128, 128), ("wood_dark", 128, 128),
    ("wood_light", 128, 128), ("leaf_green", 128, 128), ("soil", 128, 128), ("red_paint", 128, 128),
    ("concrete", 128, 128), ("cardboard", 128, 128), ("aluminium", 128, 128), ("rust", 128, 128),
    ("fabric_curtain", 128, 128), ("velvet_red", 128, 128), ("emissive_white", 128, 128), ("bulb_off", 128, 128),
    ("switch", 128, 128), ("bucket_blue", 128, 128), ("enamel_pot", 128, 128), ("key_metal", 128, 128),
    # v2: cozy guest rooms, spa department, games, luggage, phyto-bar
    ("bedspread_a", 256, 256), ("bedspread_b", 256, 256), ("upholstery_beige", 256, 256),
    ("upholstery_red", 256, 256), ("chessboard", 256, 256), ("checkers_board", 256, 256), ("backgammon", 256, 256),
    ("billiard_cloth", 512, 256), ("suitcase_a", 256, 256), ("suitcase_b", 256, 256), ("luggage_shelf", 256, 256),
    ("physio_panel", 256, 256), ("shower_console", 256, 256), ("bar_front", 512, 256), ("buvette_front", 256, 256),
    ("tea_jars", 256, 256), ("tablecloth", 256, 256), ("curtain_med", 256, 256),
    ("hydro_panel", 256, 128), ("gym_mat", 256, 128), ("travel_bag", 256, 128), ("call_panel", 256, 128),
    ("leatherette_cream", 128, 128), ("dominoes", 128, 128), ("call_button", 128, 128), ("radio_front", 128, 128),
    ("towel", 128, 128), ("brass", 128, 128), ("rubber_mat", 128, 128), ("bath_mat", 128, 128),
]

DECAL_SIZE = 2048
DECAL = [
    ("tulle", 256, 512), ("curtain_heavy", 256, 512), ("poster_1", 256, 384), ("poster_2", 256, 384),
    ("poster_3", 256, 384), ("poster_4", 256, 384), ("poster_5", 256, 384), ("poster_6", 256, 384),
    ("eye_chart", 192, 384), ("anatomy", 256, 384), ("notice_board", 512, 384), ("wall_newspaper", 384, 256),
    ("evac_plan", 384, 256), ("painting_1", 256, 192), ("painting_2", 256, 192), ("wall_carpet", 512, 384),
    ("calendar", 128, 192), ("schedule", 256, 192), ("menu_board", 256, 192), ("lift_rules", 192, 256),
    ("plant_1", 256, 256), ("plant_2", 256, 256), ("chair_legs_wood", 256, 256), ("chair_legs_tube", 256, 256),
    ("bed_head_tube", 256, 256), ("railing", 256, 256), ("wheel", 128, 128), ("papers_1", 256, 256),
    ("vent_grille", 128, 128), ("socket", 64, 64), ("light_switch", 64, 96),
    ("fire_sign", 128, 128), ("exit_sign", 256, 96), ("no_smoking", 128, 128), ("keep_out", 256, 96),
    ("lift_sign", 256, 128), ("wc_m", 96, 96), ("wc_f", 96, 96), ("wc_access", 96, 96),
    ("silence", 256, 96), ("arrow_dining", 256, 64), ("arrow_medical", 256, 64), ("arrow_admin", 256, 64),
    ("arrow_reception", 256, 64), ("arrow_hall", 256, 64), ("arrow_stairs", 256, 64), ("arrow_lift", 256, 64),
    ("roof_hatch", 256, 64), ("electro_warning", 128, 128), ("frame_photo", 128, 160),
    # v2
    ("plant_3", 256, 384), ("plant_4", 256, 256), ("poster_7", 256, 384), ("poster_8", 256, 384),
    ("poster_9", 256, 384), ("poster_10", 256, 384), ("painting_3", 512, 256), ("welcome_banner", 512, 96),
    ("menu_phyto", 256, 192), ("buvette_sign", 256, 96), ("schedule_proc", 256, 192), ("arrow_spa", 256, 64),
]

SIGN_SIZE = 2048
SIGN_W, SIGN_H = 256, 80


def pack(items, W, H, step=64):
    """Skyline bottom-left packer: tallest first, deterministic.
    Returns name -> (x0, y0, x1, y1) in pixels (y down)."""
    order = sorted(range(len(items)), key=lambda i: (-items[i][2], -items[i][1], i))
    sky = [0] * (W // step)            # filled height per column of `step` px
    out = {}
    for i in order:
        name, w, h = items[i]
        nc = -(-w // step)
        best = None
        for c0 in range(0, len(sky) - nc + 1):
            y = max(sky[c0:c0 + nc])
            if y + h <= H and (best is None or y < best[0]):
                best = (y, c0)
        if best is None:
            raise ValueError(f"atlas overflow at {name}")
        y, c0 = best
        out[name] = (c0 * step, y, c0 * step + w, y + h)
        for c in range(c0, c0 + nc):
            sky[c] = y + h
    return out


def to_uv(box, W, H, inset=1.5):
    """Pixel box -> (u0, v0, u1, v1) with v up (Blender / glTF after flip handled by exporter)."""
    x0, y0, x1, y1 = box
    return ((x0 + inset) / W, 1 - (y1 - inset) / H, (x1 - inset) / W, 1 - (y0 + inset) / H)


FURN_BOX = pack(FURN, FURN_W, FURN_H)
DECAL_BOX = pack(DECAL, DECAL_SIZE, DECAL_SIZE)
FURN_UV = {k: to_uv(v, FURN_W, FURN_H) for k, v in FURN_BOX.items()}
DECAL_UV = {k: to_uv(v, DECAL_SIZE, DECAL_SIZE) for k, v in DECAL_BOX.items()}


def sign_boxes(keys):
    cols = SIGN_SIZE // SIGN_W
    out = {}
    for i, k in enumerate(keys):
        cx, cy = i % cols, i // cols
        out[k] = (cx * SIGN_W, cy * SIGN_H, (cx + 1) * SIGN_W, (cy + 1) * SIGN_H)
        if (cy + 1) * SIGN_H > SIGN_SIZE:
            raise ValueError("sign atlas overflow")
    return out


def sign_keys(plan):
    """Every room with a number gets a door plate; plus fixed special plates."""
    return [r.rid for r in sorted(plan.rooms.values(), key=lambda r: r.rid) if r.num] + [
        "SPEC_lift_service", "SPEC_machine", "SPEC_stair1", "SPEC_stair2", "SPEC_stair3", "SPEC_shower_m",
        "SPEC_shower_f"]
