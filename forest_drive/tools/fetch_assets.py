#!/usr/bin/env python3
"""Download the CC0 source textures and scans used by the Forest Drive pipeline.

Sources (all CC0 1.0 / public domain):
  * Poly Haven  https://polyhaven.com   (textures + photoscanned models)
  * ambientCG   https://ambientcg.com   (textures)

Files go to tools/.cache/src (override with FOREST_SRC). They are inputs for
build_textures.py / build_assets.py and are NOT shipped with the game; only the
processed, packed textures in assets/textures are.

Usage:  python3 tools/fetch_assets.py
"""
from __future__ import annotations

import concurrent.futures as cf
import io
import json
import os
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get("FOREST_SRC", os.path.join(HERE, ".cache", "src"))
UA = {"User-Agent": "forest-drive-asset-fetch/1.0"}

# Poly Haven texture maps: asset -> (resolution, [maps])
PH_TEXTURES = {
    # terrain layers
    "forest_leaves_03": ("2k", ["Diffuse", "nor_gl", "arm", "Displacement"]),
    "forest_leaves_04": ("2k", ["Diffuse", "nor_gl", "arm", "Displacement"]),
    "sparse_grass": ("2k", ["Diffuse", "nor_gl", "arm", "Displacement"]),
    "mud_forest": ("2k", ["Diffuse", "nor_gl", "arm", "Displacement"]),
    "rock_ground": ("2k", ["Diffuse", "nor_gl", "arm", "Displacement"]),
    # road
    "clean_asphalt": ("2k", ["Diffuse", "nor_gl", "arm", "Displacement"]),
    "asphalt_02": ("2k", ["Diffuse", "nor_gl", "arm", "Displacement"]),
    # bark
    "pine_bark": ("2k", ["Diffuse", "nor_gl", "arm", "Displacement"]),
    "bark_brown_02": ("2k", ["Diffuse", "nor_gl", "arm", "Displacement"]),
    "tree_bark_03": ("2k", ["Diffuse", "nor_gl", "arm", "Displacement"]),
    # foliage sources (alpha-cut atlases of the scanned plants)
    "grass_medium_01": ("2k", ["Diffuse", "Alpha", "nor_gl", "Rough"]),
    "moss_01": ("2k", ["Diffuse", "Alpha", "nor_gl"]),
    "nettle_plant": ("2k", ["Diffuse", "Alpha", "nor_gl"]),
    "weed_plant_02": ("2k", ["Diffuse", "Alpha", "nor_gl"]),
    "fir_tree_01": ("4k", ["twig_diff", "twig_alpha", "twig_nor_gl", "twig_rough"]),
    "pine_tree_01": ("4k", ["twig_diff", "twig_alpha", "twig_nor_gl", "twig_rough"]),
    "fern_02": ("4k", ["Diffuse", "Alpha", "nor_gl", "Rough"]),
}
# Poly Haven photoscanned models (glTF + textures)
PH_MODELS = {
    "tree_stump_01": "2k", "tree_stump_02": "2k", "dead_tree_trunk": "2k",
    "dry_branches_medium_01": "2k", "rock_moss_set_01": "2k", "rock_moss_set_02": "2k",
    "boulder_01": "2k", "stone_01": "2k",
}
# ambientCG material sets (2K JPG zips)
ACG = ["Moss002", "Bark014", "Bark001", "Leaf001", "Leaf003"]


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception:
            if attempt == 3:
                raise
    raise RuntimeError(url)


_files_cache: dict[str, dict] = {}


def ph_files(aid: str) -> dict:
    if aid not in _files_cache:
        _files_cache[aid] = json.loads(_get("https://api.polyhaven.com/files/" + aid))
    return _files_cache[aid]


def _write(dst: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst + ".part", "wb") as f:
        f.write(data)
    os.replace(dst + ".part", dst)


def fetch_ph_map(aid: str, mp: str, res: str) -> str:
    d = ph_files(aid)
    key = {k.lower(): k for k in d}[mp.lower()]
    rs = d[key]
    r = res if res in rs else sorted(rs, key=lambda x: int(x[:-1]))[0]
    f = rs[r]["jpg"] if "jpg" in rs[r] else next(iter(rs[r].values()))
    sub = "tex4k" if r == "4k" else "tex2k"
    dst = os.path.join(SRC, sub, f"{aid}__{mp.lower()}_{r}.{f['url'].rsplit('.', 1)[1]}")
    if not os.path.exists(dst):
        _write(dst, _get(f["url"]))
    return dst


def fetch_ph_model(aid: str, res: str) -> str:
    g = ph_files(aid)["gltf"]
    r = res if res in g else sorted(g, key=lambda x: int(x[:-1]))[0]
    g = g[r]["gltf"]
    base = os.path.join(SRC, "models", aid)
    dst = os.path.join(base, aid + ".gltf")
    if not os.path.exists(dst):
        _write(dst, _get(g["url"]))
    for rel, v in g.get("include", {}).items():
        p = os.path.join(base, rel)
        if not os.path.exists(p):
            _write(p, _get(v["url"]))
    return dst


def fetch_acg(aid: str) -> str:
    base = os.path.join(SRC, "acg", aid)
    if not os.path.isdir(base):
        data = _get(f"https://ambientcg.com/get?file={aid}_2K-JPG.zip")
        os.makedirs(base, exist_ok=True)
        zipfile.ZipFile(io.BytesIO(data)).extractall(base)
    return base


def main() -> int:
    jobs = []
    with cf.ThreadPoolExecutor(8) as ex:
        for aid, (res, maps) in PH_TEXTURES.items():
            for mp in maps:
                jobs.append(ex.submit(fetch_ph_map, aid, mp, res))
        for aid, res in PH_MODELS.items():
            jobs.append(ex.submit(fetch_ph_model, aid, res))
        for aid in ACG:
            jobs.append(ex.submit(fetch_acg, aid))
        for j in cf.as_completed(jobs):
            print(j.result())
    print("sources in", SRC)
    return 0


if __name__ == "__main__":
    sys.exit(main())
