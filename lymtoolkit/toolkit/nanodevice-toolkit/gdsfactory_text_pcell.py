import pya


class GdsfactoryTextPCell(pya.PCellDeclarationHelper):
    def __init__(self):
        super(GdsfactoryTextPCell, self).__init__()
        self.param("text", self.TypeString, "Text", default="ABC123")
        self.param("x", self.TypeDouble, "Center X (um)", default=0.0)
        self.param("y", self.TypeDouble, "Center Y (um)", default=0.0)
        self.param("size_um", self.TypeDouble, "Text size (um)", default=20.0)
        self.param("layer", self.TypeLayer, "Layer", default=pya.LayerInfo(10, 0))

    def display_text_impl(self):
        return f"GdsfactoryTextPCell({self.text})"

    def coerce_parameters_impl(self):
        self.text = self.text or "ABC123"
        self.x = min(max(self.x, -1000.0), 1000.0)
        self.y = min(max(self.y, -1000.0), 1000.0)
        self.size_um = min(max(self.size_um, 0.1), 1000.0)

    def produce_impl(self):
        layout = self.layout
        dbu = layout.dbu
        layer_id = layout.layer(self.layer)
        text_region = _text_region(self.text, self.size_um, dbu)
        bbox = text_region.bbox()
        dx = int(round(self.x / dbu - (bbox.left + bbox.right) / 2.0))
        dy = int(round(self.y / dbu - (bbox.bottom + bbox.top) / 2.0))
        self.cell.shapes(layer_id).insert(text_region.moved(dx, dy))


def _text_region(text, size_um, target_dbu):
    generator = pya.TextGenerator.default_generator()
    mag = float(size_um) / max(generator.dheight(), 1e-9)
    return generator.text(text, target_dbu, mag, False, 0.0, 0.0, 0.0).merged()
