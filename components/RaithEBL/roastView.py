#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Visualize EBL-style ASCII (.asc/.acs) geometry files.
Can use PyQtGraph (fast) or Matplotlib (fallback/save).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional

# Optional fast backend
try:
    import numpy as np
except ImportError:
    np = None

try:
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtWidgets
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False

# Fallback backend
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    tk = None
    filedialog = None


@dataclass
class Poly:
    dose: float
    meta: str
    pts: List[Tuple[float, float]]


@dataclass
class Seg:
    dose: float
    meta: str
    p1: Tuple[float, float]
    p2: Tuple[float, float]


_num_re = re.compile(r"^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")


def _is_float_token(s: str) -> bool:
    return bool(_num_re.match(s))


def _parse_header(line: str) -> Tuple[str, List[str]]:
    """
    Returns (kind, tokens)
    kind: 'L' or 'POLY' or 'UNKNOWN'
    """
    s = line.strip()
    if not s:
        return "UNKNOWN", []

    tokens = s.split()
    if tokens[0].upper() == "L":
        return "L", tokens
    # polygon blocks often start with an integer like "1"
    if _is_float_token(tokens[0]) and tokens[0].lstrip("+-").isdigit():
        return "POLY", tokens

    return "UNKNOWN", tokens


def parse_asc(path: Path) -> Tuple[List[Poly], List[Seg]]:
    polys: List[Poly] = []
    segs: List[Seg] = []

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # skip empty lines
        if not line:
            i += 1
            continue

        # allow comment-style lines if they exist
        if line.startswith(("//", ";")):
            i += 1
            continue

        kind, tokens = _parse_header(line)

        if kind == "POLY":
            # Example: "1 100.0 0"
            dose = float(tokens[1]) if len(tokens) >= 2 and _is_float_token(tokens[1]) else float("nan")
            meta = " ".join(tokens)

            pts: List[Tuple[float, float]] = []
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if not s:
                    i += 1
                    continue
                if s.startswith("#"):
                    break

                xy = s.split()
                if len(xy) >= 2 and _is_float_token(xy[0]) and _is_float_token(xy[1]):
                    pts.append((float(xy[0]), float(xy[1])))
                i += 1

            # store if valid
            if len(pts) >= 2:
                polys.append(Poly(dose=dose, meta=meta, pts=pts))

            # move past '#'
            while i < len(lines) and not lines[i].strip().startswith("#"):
                i += 1
            if i < len(lines) and lines[i].strip().startswith("#"):
                i += 1
            continue

        if kind == "L":
            # Example: "L 100.000 1 0.0"
            dose = float(tokens[1]) if len(tokens) >= 2 and _is_float_token(tokens[1]) else float("nan")
            meta = " ".join(tokens)

            # next two coordinate lines until '#'
            coords: List[Tuple[float, float]] = []
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if not s:
                    i += 1
                    continue
                if s.startswith("#"):
                    break
                xy = s.split()
                if len(xy) >= 2 and _is_float_token(xy[0]) and _is_float_token(xy[1]):
                    coords.append((float(xy[0]), float(xy[1])))
                i += 1

            if len(coords) >= 2:
                segs.append(Seg(dose=dose, meta=meta, p1=coords[0], p2=coords[1]))

            # move past '#'
            while i < len(lines) and not lines[i].strip().startswith("#"):
                i += 1
            if i < len(lines) and lines[i].strip().startswith("#"):
                i += 1
            continue

        # unknown line: skip
        i += 1

    return polys, segs

def run_pyqtgraph(path: Path, polys: List[Poly], segs: List[Seg], draw_polys=True, draw_lines=True):
    # Setup PyQtGraph app
    app = pg.mkQApp("RoastView")
    win = pg.GraphicsLayoutWidget(show=True, title=f"RoastView - {path.name}")
    win.resize(1000, 800)
    plot = win.addPlot(title=f"{path.name} | polys={len(polys)}, lines={len(segs)}")
    plot.setAspectLocked(True)
    plot.showGrid(x=True, y=True)
    
    # Render polygons as a single connect="finite" path (very fast)
    if draw_polys and polys and np is not None:
        # Build giant array separated by NaNs
        xs_list = []
        ys_list = []
        for p in polys:
            if not p.pts: continue
            # Unzip points
            px, py = zip(*p.pts)
            xs_list.extend(px)
            xs_list.append(np.nan) # break line
            ys_list.extend(py)
            ys_list.append(np.nan)
        
        arr_x = np.array(xs_list, dtype=np.float32)
        arr_y = np.array(ys_list, dtype=np.float32)
        
        plot.plot(arr_x, arr_y, pen=pg.mkPen('c', width=1), connect="finite", name="Polygons")

    # Render segments
    if draw_lines and segs and np is not None:
        # Build giant array: p1, p2, nan, p1, p2, nan...
        count = len(segs)
        p1s = np.array([s.p1 for s in segs])
        p2s = np.array([s.p2 for s in segs])
        nans = np.full(count, np.nan)
        
        # Interleave columns
        seg_x = np.column_stack((p1s[:,0], p2s[:,0], nans)).flatten()
        seg_y = np.column_stack((p1s[:,1], p2s[:,1], nans)).flatten()
        
        plot.plot(seg_x, seg_y, pen=pg.mkPen('m', width=1), connect="finite", name="Segments")
        
    pg.exec()

def run_matplotlib(path: Path, polys: List[Poly], segs: List[Seg], args, draw_polys, draw_lines):
    if plt is None:
        print("Error: Matplotlib not available.")
        return

    # Use collections for speed if possible
    from matplotlib.collections import PolyCollection, LineCollection
    
    fig, ax = plt.subplots()

    # Draw polygons (outline)
    if draw_polys and polys:
        # Optimization: use PolyCollection
        verts = [p.pts for p in polys]
        pc = PolyCollection(verts, edgecolors='tab:blue', facecolors='none', linewidths=1)
        ax.add_collection(pc)
        ax.autoscale_view()

    # Draw line segments
    if draw_lines and segs:
        # Optimization: use LineCollection
        segments = [(s.p1, s.p2) for s in segs]
        lc = LineCollection(segments, colors='tab:orange', linewidths=0.8)
        ax.add_collection(lc)
        ax.autoscale_view()
        
    # If standard fallback needed (slow loop), not used here.

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title(f"{path.name}  |  polys={len(polys)}, lines={len(segs)}")

    if args.equal:
        ax.set_aspect("equal", adjustable="box")

    ax.grid(True, linewidth=0.3)
    ax.autoscale() # Ensure limits update for collections

    if args.save:
        out = Path(args.save)
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"Saved: {out.resolve()}")

    plt.show()

def main():
    ap = argparse.ArgumentParser(description="Visualize EBL-style ASCII (.asc/.acs) geometry file.")
    ap.add_argument("input", type=str, nargs="?", help="Path to .asc/.acs file")
    ap.add_argument("--show-polys", action="store_true", help="Draw polygon outlines (default: on)")
    ap.add_argument("--no-polys", action="store_true", help="Disable polygon drawing")
    ap.add_argument("--no-lines", action="store_true", help="Disable line drawing")
    ap.add_argument("--equal", action="store_true", help="Use equal axis scale (recommended)")
    ap.add_argument("--save", type=str, default="", help="Save figure to file (png/pdf/svg). e.g. out.png")
    ap.add_argument("--max-lines", type=int, default=0, help="Draw only first N lines (0 = all)")
    ap.add_argument("--max-polys", type=int, default=0, help="Draw only first N polys (0 = all)")
    ap.add_argument("--backend", choices=["mpl", "pg"], default="pg" if HAS_PYQTGRAPH else "mpl", 
                    help="Plotting backend: 'pg' (PyQtGraph, fast) or 'mpl' (Matplotlib, slow/export)")
    args = ap.parse_args()

    file_path = args.input

    # File selection if not provided
    if not file_path:
        # Prefer Qt dialog if we might use PyQtGraph or if tk is missing
        if HAS_PYQTGRAPH and (tk is None or args.backend == 'pg'):
            app = pg.mkQApp("RoastView") # Ensure app exists
            fname, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Select Raith ASCII file", "", "Raith ASCII (*.asc *.acs);;All files (*.*)")
            if fname:
                file_path = fname
        elif tk:
            # Fallback to Tk
            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.askopenfilename(
                title="Select Raith ASCII file",
                filetypes=[("Raith ASCII", "*.asc *.acs"), ("All files", "*.*")]
            )
            root.destroy()
        else:
             print("Error: No input file provided and no GUI toolkit available.")
             sys.exit(1)
        
    if not file_path:
        print("No file selected.")
        return

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    print(f"Parsing {path.name}...")
    polys, segs = parse_asc(path)
    print(f"Found {len(polys)} polygons, {len(segs)} segments.")

    draw_polys = True
    if args.no_polys:
        draw_polys = False
    if args.show_polys:
        draw_polys = True

    draw_lines = not args.no_lines

    if args.max_polys and args.max_polys > 0:
        polys = polys[: args.max_polys]
    if args.max_lines and args.max_lines > 0:
        segs = segs[: args.max_lines]

    # Select backend
    if args.save:
        # Always use matplotlib for saving files (PyQtGraph export is more complex/limited)
        print("Saving requested, using Matplotlib backend...")
        run_matplotlib(path, polys, segs, args, draw_polys, draw_lines)
    elif args.backend == "pg" and HAS_PYQTGRAPH and np is not None:
        print("Using PyQtGraph backend (fast)...")
        run_pyqtgraph(path, polys, segs, draw_polys, draw_lines)
    else:
        print("Using Matplotlib backend...")
        run_matplotlib(path, polys, segs, args, draw_polys, draw_lines)


if __name__ == "__main__":
    main()
