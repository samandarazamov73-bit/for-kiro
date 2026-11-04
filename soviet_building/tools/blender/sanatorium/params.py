"""Shared dimensions. Values mirror tools/cmd/build/params.go and specs.go.

Coordinates are the original modelling axes, which are also Blender's axes after
importing SovietSchool.glb: X right, Y back, Z up. The main facade lies at Y=0 and
faces -Y; the entrance block projects towards -Y.
"""

# --- exterior (from the Go generator, do not change) -------------------------
BAY = 3.0
FLOOR_H = 3.3
FFL = 1.20
MAIN_LEN = 75.0
MAIN_DEPTH = 16.2
MAIN_BAYS = 25
MAIN_ROOF_Z = 14.60
HALL_BAY = 3.25
ENT_X0, ENT_X1 = 27.0, 39.0
ENT_Y0 = -19.5
ENT_ROOF_Z = 11.60
GLAZ_X = 27.5                      # recessed lobby curtain wall plane
REC_S0, REC_S1 = 0.9, 11.7         # curtain wall extent along -Y
REC_TOP_Z = 4.00
HALL_BASE = 6.00
WIN_BASE = 0.60                    # window surround bottom above floor level
REAR_EXITS = (4.5, 70.5)           # rear steel doors (world X)
STAIR_HOUSES = ((33.0, 7.8), (66.0, 7.2))  # roof exit enclosures (3.0 x 2.4)

LEVELS = [FFL + i * FLOOR_H for i in range(4)]   # 1.2, 4.5, 7.8, 11.1
FLOOR_NAMES = ["1", "2", "3", "4"]

# Standard window (StdWin) glass opening relative to the window centre / base.
STD_HALF_W = 2.45 / 2 - 0.23       # 0.995
STD_Z0 = 0.25 + 0.08               # sill member + slope -> 0.33 above surround base
STD_Z1 = 2.55 - 0.23               # 2.32
# Hall window (HallWin)
HALL_HALF_W = 2.40 / 2 - 0.18      # 1.02
HALL_Z0 = 0.20 + 0.07
HALL_Z1 = 5.00 - 0.18
GLASS_RECESS = 0.14                # glass plane behind the facade plane

# --- interior (new) ----------------------------------------------------------
EXT_T = 0.35        # exterior wall thickness (interior face offset)
CEIL_H = 3.0        # clear height of a standard storey
SLAB_T = 0.3
PART_T = 0.12       # brick partitions
CORR_T = 0.2        # corridor walls (load-bearing)
CORR_Y0, CORR_Y1 = 6.7, 9.5        # corridor clear width 2.8 m
FRONT_Y0, FRONT_Y1 = EXT_T, CORR_Y0 - CORR_T     # 0.35 .. 6.5
REAR_Y0, REAR_Y1 = CORR_Y1 + CORR_T, MAIN_DEPTH - EXT_T  # 9.7 .. 15.85
MAIN_X0, MAIN_X1 = EXT_T, MAIN_LEN - EXT_T
ENT_IX0, ENT_IX1 = ENT_X0 + EXT_T, ENT_X1 - EXT_T  # 27.35 .. 38.65
ENT_IY0 = ENT_Y0 + EXT_T                           # -19.15
HALL_CEIL = 11.2
COLUMN = 0.4

# stairs (one module for all three cells)
RISER = 0.15
TREAD = 0.30
RISERS_PER_FLIGHT = 11
FLIGHT_W = 1.44
FLIGHT_GAP = 0.10
STAIR_LANDING = 1.44
STAIR_RUN = (RISERS_PER_FLIGHT - 1) * TREAD   # 3.0

# elevator
SHAFT = (36.2, 38.8, 3.7, 6.5)     # x0, x1, y0, y1 (clear)
SHAFT_PIT_Z = FFL - 1.4
SHAFT_TOP_Z = 14.3
LIFT_DOOR_X = 37.5
LIFT_DOOR_W = 1.1
LIFT_DOOR_H = 2.0


def bay_x(k):
    """Left/right clear X of main wing bay k (partitions on bay lines)."""
    x0 = k * BAY + (PART_T / 2 if k > 0 else EXT_T)
    x1 = (k + 1) * BAY - (PART_T / 2 if k < MAIN_BAYS - 1 else EXT_T)
    return x0, x1
