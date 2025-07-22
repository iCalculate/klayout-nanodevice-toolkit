import pya
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../utils')))
from text_utils import TextUtils
from utils.geometry import GeometryUtils

class TextPCell(pya.PCellDeclarationHelper):
    def __init__(self):
        super(TextPCell, self).__init__()
        self.param("text", self.TypeString, "Text", default="Hello KLayout")
        self.param("x", self.TypeDouble, "X (um)", default=0.0)
        self.param("y", self.TypeDouble, "Y (um)", default=0.0)
        self.param("size_um", self.TypeDouble, "Font size (um)", default=10.0)
        self.param("font_path", self.TypeString, "Font path", default="C:/Windows/Fonts/OCRAEXT.TTF")
        self.param("spacing_um", self.TypeDouble, "Char spacing (um)", default=-5.0)
        self.param("layer", self.TypeLayer, "Layer", default=pya.LayerInfo(10, 0))

    def display_text_impl(self):
        return f"TextPCell: {self.text}"

    def produce_impl(self):
        GeometryUtils.UNIT_SCALE = 1000
        ly = self.layout
        cell = self.cell
        layer = self.layer
        print(f"[DEBUG] layout.dbu: {ly.dbu}")
        print(f"[DEBUG] PCell param size_um: {self.size_um}")
        polys = TextUtils.create_text_freetype(
            self.text,
            self.x/10.0,
            self.y/10.0,
            size_um=self.size_um/4.0,
            font_path=self.font_path,
            spacing_um=(self.spacing_um/10.0),
            anchor='left_bottom'
        )
        print(f"[DEBUG] polygons count: {len(polys)}")
        for poly in polys:
            cell.shapes(layer).insert(poly) 