"""
prepare_dataset.py  -  audit + leakage-safe train/val/test split.

Input : ml/dataset/<Crop___Condition>/*.jpg (only the classes listed in model/class_config.json)      (ORIGINAL data, never modified)
Output: ml/dataset_split/{train,val,test}/<class_name>/*.jpg   (generated copies)
        ml/dataset_split/split_summary.json, dataset_audit.json

WHY THIS IS MORE THAN A RANDOM SPLIT
PlantVillage-style data contains many near-duplicates: the same leaf photo
rotated, flipped, re-cropped or re-exported. A plain random split would put
copies of one photo into both train and test, inflating test accuracy.

What we do:
  1. Decode every image once (corrupt files are reported and skipped).
  2. Compute a 64-bit perceptual hash (DCT/pHash) of a 32x32 greyscale copy.
  3. Also hash all 8 rotations/flips of each image, so a rotated or
     mirrored copy still matches the original.
  4. Union images whose hash distance is <= HASH_THRESHOLD into clusters
     (per class; exact cross-class duplicates are detected separately and dropped).
  5. Split whole CLUSTERS (never single files) 70/15/15, stratified per class.

Limitation (stated honestly): perceptual hashing catches copies/augmentations
of the same photo. It cannot detect two different photographs of the same
physical leaf. Test accuracy on this dataset is therefore still likely
optimistic compared with real field photos.

Usage (from ml/):
    python training/prepare_dataset.py --input ./dataset --output ./dataset_split
"""
import argparse
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ML_DIR = Path(__file__).resolve().parents[1]

SEED = 42
RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}
HASH_THRESHOLD = 6          # max Hamming distance (of 64 bits) to call two images "the same photo"
HASH_SIZE = 32              # DCT input side
IMG_EXT = {".jpg", ".jpeg", ".png"}

_CFG = json.loads((ML_DIR.parent / "model" / "class_config.json").read_text(encoding="utf-8"))
FOLDER_TO_CLASS = {c["source_folder"]: c["class_name"] for c in _CFG["classes"]}


# ---------------------------------------------------------------- hashing
def _dct_matrix(n: int) -> np.ndarray:
    k = np.arange(n)[:, None]
    i = np.arange(n)[None, :]
    m = np.cos(np.pi * (2 * i + 1) * k / (2 * n)) * np.sqrt(2.0 / n)
    m[0] /= np.sqrt(2)
    return m


_DCT = _dct_matrix(HASH_SIZE)


def _phash_bits(gray: np.ndarray) -> int:
    d = _DCT @ gray @ _DCT.T
    low = d[:8, :8].flatten()
    bits = low > np.median(low[1:])          # ignore DC term in the median
    out = 0
    for b in bits:
        out = (out << 1) | int(b)
    return out


def _dihedral(a: np.ndarray):
    for k in range(4):
        r = np.rot90(a, k)
        yield r
        yield np.fliplr(r)


def hash_image(path: Path):
    """Returns (size, [8 hashes]) or None if the image is unreadable."""
    try:
        with Image.open(path) as im:
            size = im.size
            im.draft("L", (128, 128))
            im = ImageOps.exif_transpose(im).convert("L").resize((HASH_SIZE, HASH_SIZE), Image.LANCZOS)
            g = np.asarray(im, dtype=np.float64)
        return size, [_phash_bits(v) for v in _dihedral(g)]
    except Exception:
        return None


_POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def _popcount64(x: np.ndarray) -> np.ndarray:
    x = np.ascontiguousarray(x)
    return _POP[x.view(np.uint8).reshape(*x.shape, 8)].sum(-1)


def cluster_duplicates(hashes: np.ndarray):
    """hashes: (n, 8) uint64  -> cluster id per image (union-find)."""
    n = hashes.shape[0]
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    base = hashes[:, 0]
    CH = 256
    for s in range(0, n, CH):
        blk = base[s:s + CH][:, None]                        # (ch,1)
        best = None
        for k in range(8):                                   # any of the 8 orientations
            dist = _popcount64(blk ^ hashes[:, k][None, :])  # (ch, n)
            best = dist if best is None else np.minimum(best, dist)
        ii, jj = np.nonzero(best <= HASH_THRESHOLD)
        for a, b in zip(ii + s, jj):
            if a != b:
                ra, rb = find(int(a)), find(int(b))
                if ra != rb:
                    parent[ra] = rb
    return np.array([find(i) for i in range(n)])


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(ML_DIR / "dataset"))
    ap.add_argument("--output", default=str(ML_DIR / "dataset_split"))
    args = ap.parse_args()
    src_root, out_root = Path(args.input), Path(args.output)

    items = []  # (path, class_name)
    missing = []
    for folder, cls in FOLDER_TO_CLASS.items():
        d = src_root / folder
        if not d.is_dir():
            missing.append(folder)
            continue
        for p in sorted(d.iterdir()):
            if p.suffix.lower() in IMG_EXT:
                items.append((p, cls))
    if missing:
        print("WARNING: missing class folders:", missing)
    if not items:
        raise SystemExit(f"No images found in {src_root}. See ml/dataset/README.md")

    print(f"Found {len(items)} images in {len(FOLDER_TO_CLASS) - len(missing)} classes. Hashing...")
    valid, hashes, sizes, corrupt = [], [], Counter(), []
    for i, (p, cls) in enumerate(items):
        r = hash_image(p)
        if r is None:
            corrupt.append(str(p))
            continue
        sizes[f"{r[0][0]}x{r[0][1]}"] += 1
        valid.append((p, cls))
        hashes.append(r[1])
        if (i + 1) % 2000 == 0:
            print(f"  hashed {i + 1}/{len(items)}", flush=True)
    H = np.array(hashes, dtype=np.uint64)

    print("Clustering near-duplicates (per class) ...", flush=True)
    cls_idx = defaultdict(list)
    for i, (_, c) in enumerate(valid):
        cls_idx[c].append(i)
    clusters, cross_class = {}, []
    for c, ids in cls_idx.items():
        local = cluster_duplicates(H[ids])
        for j, lc in zip(ids, local):
            clusters.setdefault((c, int(lc)), []).append(j)
    clusters = {k: v for k, v in clusters.items()}
    # exact cross-class duplicate check: identical canonical (min over 8 orientations) hash
    canon = defaultdict(set)
    for i in range(len(valid)):
        canon[int(H[i].min())].add(valid[i][1])
    cross_hashes = {h for h, cs in canon.items() if len(cs) > 1}
    drop_idx = {i for i in range(len(valid)) if int(H[i].min()) in cross_hashes}
    cross_class = list(cross_hashes)
    multi = [v for v in clusters.values() if len(v) > 1]
    largest = max(len(v) for v in clusters.values())
    print(f"  {len(clusters)} clusters; {len(multi)} contain duplicates "
          f"({sum(len(v) for v in multi)} images); {len(cross_class)} hashes appear under >1 class; "
          f"largest cluster = {largest}", flush=True)

    dropped_cross = len(drop_idx)
    by_class = defaultdict(list)
    for (c, _), v in clusters.items():
        v = [i for i in v if i not in drop_idx]
        if v:
            by_class[c].append(v)

    rng = random.Random(SEED)
    if out_root.exists():
        shutil.rmtree(out_root)
    summary = {}
    for cls, groups in sorted(by_class.items()):
        rng.shuffle(groups)
        total = sum(len(g) for g in groups)
        targets = {k: total * r for k, r in RATIOS.items()}
        got = {k: 0 for k in RATIOS}
        assign = defaultdict(list)
        for g in sorted(groups, key=len, reverse=True):      # big clusters first -> tight quotas
            k = max(RATIOS, key=lambda s: (targets[s] - got[s]) / max(targets[s], 1))
            assign[k].append(g)
            got[k] += len(g)
        for split, gl in assign.items():
            dst = out_root / split / cls
            dst.mkdir(parents=True, exist_ok=True)
            for g in gl:
                for i in g:
                    shutil.copy2(valid[i][0], dst / valid[i][0].name)
        summary[cls] = {"images": total, "clusters": len(groups), **got}
        print(f"  {cls:24s} train={got['train']:5d} val={got['val']:4d} test={got['test']:4d}")

    # Leakage self-check: no duplicate cluster may span two splits.
    split_of = {}
    for split in RATIOS:
        for f in (out_root / split).rglob("*"):
            if f.is_file():
                split_of[(f.parent.name, f.name)] = split
    leaked = 0
    for v in multi:
        ss = {split_of.get((valid[i][1], valid[i][0].name)) for i in v} - {None}
        if len(ss) > 1:
            leaked += 1
    print(f"Leakage self-check: {leaked} duplicate clusters span multiple splits (must be 0)")

    counts = {c: s["images"] for c, s in summary.items()}
    audit = {
        "total_images_found": len(items),
        "unreadable_files": corrupt,
        "image_size_distribution": dict(sizes.most_common(10)),
        "duplicate_clusters_with_more_than_one_image": len(multi),
        "images_in_duplicate_clusters": sum(len(v) for v in multi),
        "largest_cluster_size": largest,
        "cross_class_duplicate_hashes_dropped": len(cross_class),
        "images_dropped_cross_class": dropped_cross,
        "hash_threshold_bits": HASH_THRESHOLD,
        "class_counts_after_cleaning": counts,
        "imbalance_ratio_max_over_min": round(max(counts.values()) / min(counts.values()), 2),
        "leaked_clusters_after_split": leaked,
        "seed": SEED,
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "split_summary.json").write_text(json.dumps(summary, indent=2))
    (out_root / "dataset_audit.json").write_text(json.dumps(audit, indent=2))
    print("\nAudit written to", out_root / "dataset_audit.json")
    if leaked:
        raise SystemExit("Leakage detected - do not train on this split.")


if __name__ == "__main__":
    main()
