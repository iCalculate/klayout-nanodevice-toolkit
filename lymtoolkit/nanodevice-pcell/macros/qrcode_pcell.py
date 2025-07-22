import pya
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../utils')))
from QRcode_utils import QRCodeUtils
from utils.geometry import GeometryUtils

class QRCodePCell(pya.PCellDeclarationHelper):
    def __init__(self):
        super(QRCodePCell, self).__init__()
        self.param("text", self.TypeString, "QR Content", default="https://github.com/iCalculate/klayout-nanodevice-toolkit")
        self.param("box_size", self.TypeDouble, "Box size (um)", default=10.0)
        self.param("version", self.TypeInt, "QR version", default=2)
        self.param("border", self.TypeInt, "Border width (pixels)", default=4)
        self.param("layer", self.TypeLayer, "Layer", default=pya.LayerInfo(10, 0))

    def display_text_impl(self):
        return f"QRCodePCell: {self.text}"

    def produce_impl(self):
        GeometryUtils.UNIT_SCALE = 100
        ly = self.layout
        cell = self.cell
        layer = self.layer
        matrix = QRCodeUtils.generate_qr_matrix(self.text, version=self.version, box_size=self.box_size, border=self.border)
        polys = QRCodeUtils.qr_matrix_to_polygons(matrix, x0=0, y0=0, box_size=self.box_size)
        for poly in polys:
            cell.shapes(layer).insert(poly) 