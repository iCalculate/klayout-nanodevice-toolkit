# -*- coding: utf-8 -*-
"""
LabPDK technology registration.
Run this from KLayout (e.g. via register_labpdk.lym) to load and register
the LabPDK technology so it appears in the technology list and new layouts
use dbu=0.001 and the layer map.
"""
import os
import pya

def register_labpdk():
    """Load and register LabPDK technology. Idempotent."""
    if pya.Technology.has_technology("LabPDK"):
        return  # already registered
    # PDK root = parent of macros/
    this_dir = os.path.dirname(os.path.abspath(__file__))
    pdk_root = os.path.dirname(this_dir)
    lyt_path = os.path.join(pdk_root, "technology.lyt")
    if not os.path.isfile(lyt_path):
        raise FileNotFoundError("LabPDK technology.lyt not found: %s" % lyt_path)
    tech = pya.Technology()
    tech.load(lyt_path)
    pya.Technology.register_technology(tech)
    print("[LabPDK] Technology registered from %s" % lyt_path)

if __name__ != "__main__":
    register_labpdk()
