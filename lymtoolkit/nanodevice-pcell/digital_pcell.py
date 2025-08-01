import pya
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../utils')))
from digital_utils import DigitalDisplay
from utils.geometry import GeometryUtils

class DigitalPCell(pya.PCellDeclarationHelper):
    def __init__(self):
        super(DigitalPCell, self).__init__()
        self.param("text", self.TypeString, "Text (digits/letters)", default="NANO DEVICE")
        self.param("x", self.TypeDouble, "X (um)", default=0.0)
        self.param("y", self.TypeDouble, "Y (um)", default=0.0)
        self.param("size", self.TypeDouble, "Size (um)", default=10.0)
        self.param("stroke_width", self.TypeDouble, "Stroke width (um)", default=5.0)
        self.param("spacing", self.TypeDouble, "Char spacing (um)", default=17.0)
        self.param("layer", self.TypeLayer, "Layer", default=pya.LayerInfo(10, 0))

    def display_text_impl(self):
        return f"DigitalPCell: {self.text}"

    def produce_impl(self):
        GeometryUtils.UNIT_SCALE = 1000
        ly = self.layout
        cell = self.cell
        layer = self.layer
        polys = DigitalDisplay.create_digits(self.text, self.x, self.y, size=self.size, stroke_width=self.stroke_width, spacing=self.spacing)
        for poly in polys:
            cell.shapes(layer).insert(poly) 