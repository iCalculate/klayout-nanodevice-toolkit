# -*- coding: utf-8 -*-
"""
Meander device component module - KLayout-based meander pattern generator
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import klayout.db as db
import pya
from utils.geometry import GeometryUtils
from utils.mark_utils import MarkUtils
from utils.text_utils import TextUtils
from config import LAYER_DEFINITIONS

class Meander:
    """Meander device class for generating serpentine patterns"""
    
    def __init__(self, layout=None, **kwargs):
        """
        Initialize Meander device class
        
        Args:
            layout: KLayout layout object, create new if None
            **kwargs: Other parameters including device, mark, fanout, labeling parameters
        """
        self.layout = layout or db.Layout()
        # Set database unit: 1 dbu = 1 μm
        self.layout.dbu = 1.0
        # Set geometry tool unit scale: 1 μm = 1 database unit
        GeometryUtils.UNIT_SCALE = 1.0
        MarkUtils.set_unit_scale(1.0)
        TextUtils.set_unit_scale(1.0)
        self.setup_layers()
        
        # ===== Meander core parameters =====
        self.region_width = kwargs.get('region_width', 200.0)        # Rectangle region width (μm)
        self.region_height = kwargs.get('region_height', 100.0)      # Rectangle region height (μm)
        self.line_width = kwargs.get('line_width', 5.0)              # Line width (μm)
        self.line_spacing = kwargs.get('line_spacing', 10.0)         # Line spacing (μm)
        self.direction = kwargs.get('direction', 'horizontal')       # Starting direction 'horizontal' or 'vertical'
        self.margin = kwargs.get('margin', 0.0)                      # Margin (μm)
        self.curve_type = kwargs.get('curve_type', 'serpentine')     # Curve type 'serpentine', 'peano', 'hilbert', 'gosper', 'moore'
        
        # Backward compatibility
        self.channel_length = self.region_width
        self.channel_width = self.line_width
        self.channel_spacing = self.line_spacing
        self.turns = 5  # No longer used
        
    def setup_layers(self):
        """Setup layers"""
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            # In KLayout, use layer() method to get or create layers
            # layer() method requires (layer_number, datatype) parameters
            self.layout.layer(layer_info['id'], 0)  # Use datatype=0
    
    def set_serpentine_parameters(self, region_width=None, region_height=None, line_width=None, 
                                 line_spacing=None, direction=None, margin=None, curve_type=None):
        """
        Set meander parameters
        
        Args:
            region_width: Rectangle region width (μm)
            region_height: Rectangle region height (μm)
            line_width: Line width (μm)
            line_spacing: Line spacing (μm)
            direction: Starting direction 'horizontal' or 'vertical'
            margin: Margin (μm)
            curve_type: Curve type 'serpentine', 'peano', 'hilbert', 'gosper', 'moore'
        """
        if region_width is not None:
            self.region_width = region_width
            self.channel_length = region_width  # Maintain compatibility
        if region_height is not None:
            self.region_height = region_height
        if line_width is not None:
            self.line_width = line_width
            self.channel_width = line_width  # Maintain compatibility
        if line_spacing is not None:
            self.line_spacing = line_spacing
            self.channel_spacing = line_spacing  # Maintain compatibility
        if direction is not None:
            self.direction = direction
        if margin is not None:
            self.margin = margin
        if curve_type is not None:
            self.curve_type = curve_type
    
    def create_serpentine_channel(self, cell, x=0.0, y=0.0):
        """
        Create meander channel
        
        Args:
            cell: Target cell
            x, y: Device center coordinates
        """
        layer_id = LAYER_DEFINITIONS['channel']['id']
        
        # Create meander channel based on curve type
        if self.curve_type == 'serpentine':
            serpentine = GeometryUtils._create_serpentine_curve(
                x, y, self.region_width, self.region_height, 
                self.line_width, self.line_spacing, self.direction, 
                'rect', self.margin  # Only support rectangular turns
            )
        elif self.curve_type == 'peano':
            serpentine = GeometryUtils._create_peano_curve(
                x, y, self.region_width, self.line_width, self.line_spacing, self.turns
            )
        elif self.curve_type == 'gosper':
            serpentine = GeometryUtils._create_gosper_curve(
                x, y, self.region_width, self.line_width, self.line_spacing, self.turns
            )
        elif self.curve_type == 'moore':
            serpentine = GeometryUtils._create_moore_curve(
                x, y, self.region_width, self.line_width, self.line_spacing, self.turns
            )
        else:
            # Other curve types use original method
            serpentine = GeometryUtils.create_serpentine_channel(
                x, y, self.channel_length, self.channel_width, 
                self.channel_spacing, self.turns, self.direction, self.curve_type
            )
        cell.shapes(layer_id).insert(serpentine)


def main():
    """Main function - Generate all curve type test structures"""
    
    print("=== Generating All Curve Type Test Structures ===")
    
    # Create Meander device instance
    meander = Meander()
    
    # Create top-level test cell
    top_cell = meander.layout.create_cell("Test_All_Curves")
    
    # ===== Generate Hilbert curve =====
    print("Generating Hilbert curve...")
    try:
        hilbert_cell = meander.layout.create_cell("Hilbert_Test")
        
        # Hilbert parameters: order=5, step=10μm, line_w=4μm, margin=2μm
        hilbert_region = GeometryUtils.make_hilbert(
            order=5,
            step=10.0,
            line_w=4.0,
            margin=2.0
        )
        
        layer_id = LAYER_DEFINITIONS['channel']['id']
        hilbert_cell.shapes(layer_id).insert(hilbert_region)
        top_cell.insert(pya.CellInstArray(hilbert_cell.cell_index(), pya.Trans()))
        
        print("✓ Hilbert curve generated successfully")
        
    except Exception as e:
        print(f"✗ Hilbert curve generation failed: {e}")
        return
    
    # ===== Generate Serpentine curve =====
    print("Generating Serpentine curve...")
    try:
        serpentine_cell = meander.layout.create_cell("Serpentine_Test")
        
        # Serpentine parameters: 300x300μm, 4μm line width, 5μm spacing, horizontal direction
        meander.set_serpentine_parameters(
            region_width=300.0,
            region_height=300.0,
            line_width=4.0,
            line_spacing=5.0,
            direction='horizontal',
            margin=0.0,
            curve_type='serpentine'
        )
        
        meander.create_serpentine_channel(serpentine_cell, 0.0, 0.0)
        top_cell.insert(pya.CellInstArray(serpentine_cell.cell_index(), pya.Trans(pya.Point(500, 0))))
        
        print("✓ Serpentine curve generated successfully")
        
    except Exception as e:
        print(f"✗ Serpentine curve generation failed: {e}")
        return
    
    # ===== Generate Peano curve =====
    print("Generating Peano curve...")
    try:
        peano_cell = meander.layout.create_cell("Peano_Test")
        
        # Peano parameters: 300x300μm, 4μm line width, 5μm spacing
        meander.set_serpentine_parameters(
            region_width=300.0,
            region_height=300.0,
            line_width=4.0,
            line_spacing=5.0,
            direction='horizontal',
            margin=0.0,
            curve_type='peano'
        )
        
        meander.create_serpentine_channel(peano_cell, 0.0, 0.0)
        top_cell.insert(pya.CellInstArray(peano_cell.cell_index(), pya.Trans(pya.Point(1000, 0))))
        
        print("✓ Peano curve generated successfully")
        
    except Exception as e:
        print(f"✗ Peano curve generation failed: {e}")
        return
    
    # ===== Generate Gosper curve =====
    print("Generating Gosper curve...")
    try:
        gosper_cell = meander.layout.create_cell("Gosper_Test")
        
        # Gosper parameters: 300x300μm, 4μm line width, 5μm spacing
        meander.set_serpentine_parameters(
            region_width=300.0,
            region_height=300.0,
            line_width=4.0,
            line_spacing=5.0,
            direction='horizontal',
            margin=0.0,
            curve_type='gosper'
        )
        
        meander.create_serpentine_channel(gosper_cell, 0.0, 0.0)
        top_cell.insert(pya.CellInstArray(gosper_cell.cell_index(), pya.Trans(pya.Point(1500, 0))))
        
        print("✓ Gosper curve generated successfully")
        
    except Exception as e:
        print(f"✗ Gosper curve generation failed: {e}")
        return
    
    # ===== Generate Moore curve =====
    print("Generating Moore curve...")
    try:
        moore_cell = meander.layout.create_cell("Moore_Test")
        
        # Moore parameters: 300x300μm, 4μm line width, 5μm spacing
        meander.set_serpentine_parameters(
            region_width=300.0,
            region_height=300.0,
            line_width=4.0,
            line_spacing=5.0,
            direction='horizontal',
            margin=0.0,
            curve_type='moore'
        )
        
        meander.create_serpentine_channel(moore_cell, 0.0, 0.0)
        top_cell.insert(pya.CellInstArray(moore_cell.cell_index(), pya.Trans(pya.Point(2000, 0))))
        
        print("✓ Moore curve generated successfully")
        
    except Exception as e:
        print(f"✗ Moore curve generation failed: {e}")
        return
    
    # ===== Generate Hilbert parameter scan test =====
    print("Generating Hilbert parameter scan test...")
    try:
        # Create Hilbert parameter scan cell
        hilbert_scan_cell = meander.layout.create_cell("Hilbert_Parameter_Scan")
        
        # Define parameter scan ranges
        orders = [3, 4, 5, 6]  # Hilbert curve orders
        steps = [8.0, 10.0, 12.0, 15.0]  # Step sizes
        line_widths = [2.0, 3.0, 4.0, 5.0]  # Line widths
        margins = [1.0, 2.0, 3.0]  # Margins
        
        # Calculate layout parameters
        cell_spacing_x = 800.0  # Cell horizontal spacing
        cell_spacing_y = 800.0  # Cell vertical spacing
        start_x = 0.0
        start_y = 0.0
        
        # Parameter scan: order variation
        print("  Generating Hilbert curves with different orders...")
        for i, order in enumerate(orders):
            hilbert_sub_cell = meander.layout.create_cell(f"Hilbert_Order_{order}")
            
            # Generate Hilbert curve
            hilbert_region = GeometryUtils.make_hilbert(
                order=order,
                step=10.0,  # Fixed step size
                line_w=3.0,  # Fixed line width
                margin=2.0   # Fixed margin
            )
            
            layer_id = LAYER_DEFINITIONS['channel']['id']
            hilbert_sub_cell.shapes(layer_id).insert(hilbert_region)
            
            # Calculate position
            x = start_x + i * cell_spacing_x
            y = start_y
            
            # Insert into scan cell
            hilbert_scan_cell.insert(pya.CellInstArray(
                hilbert_sub_cell.cell_index(), 
                pya.Trans(pya.Point(int(x), int(y)))
            ))
        
        # Parameter scan: step size variation
        print("  Generating Hilbert curves with different step sizes...")
        for i, step in enumerate(steps):
            hilbert_sub_cell = meander.layout.create_cell(f"Hilbert_Step_{step}")
            
            # Generate Hilbert curve
            hilbert_region = GeometryUtils.make_hilbert(
                order=4,  # Fixed order
                step=step,
                line_w=3.0,  # Fixed line width
                margin=2.0   # Fixed margin
            )
            
            layer_id = LAYER_DEFINITIONS['channel']['id']
            hilbert_sub_cell.shapes(layer_id).insert(hilbert_region)
            
            # Calculate position
            x = start_x + i * cell_spacing_x
            y = start_y + cell_spacing_y
            
            # Insert into scan cell
            hilbert_scan_cell.insert(pya.CellInstArray(
                hilbert_sub_cell.cell_index(), 
                pya.Trans(pya.Point(int(x), int(y)))
            ))
        
        # Parameter scan: line width variation
        print("  Generating Hilbert curves with different line widths...")
        for i, line_w in enumerate(line_widths):
            hilbert_sub_cell = meander.layout.create_cell(f"Hilbert_LineW_{line_w}")
            
            # Generate Hilbert curve
            hilbert_region = GeometryUtils.make_hilbert(
                order=4,  # Fixed order
                step=10.0,  # Fixed step size
                line_w=line_w,
                margin=2.0   # Fixed margin
            )
            
            layer_id = LAYER_DEFINITIONS['channel']['id']
            hilbert_sub_cell.shapes(layer_id).insert(hilbert_region)
            
            # Calculate position
            x = start_x + i * cell_spacing_x
            y = start_y + 2 * cell_spacing_y
            
            # Insert into scan cell
            hilbert_scan_cell.insert(pya.CellInstArray(
                hilbert_sub_cell.cell_index(), 
                pya.Trans(pya.Point(int(x), int(y)))
            ))
        
        # Parameter scan: margin variation
        print("  Generating Hilbert curves with different margins...")
        for i, margin in enumerate(margins):
            hilbert_sub_cell = meander.layout.create_cell(f"Hilbert_Margin_{margin}")
            
            # Generate Hilbert curve
            hilbert_region = GeometryUtils.make_hilbert(
                order=4,  # Fixed order
                step=10.0,  # Fixed step size
                line_w=3.0,  # Fixed line width
                margin=margin
            )
            
            layer_id = LAYER_DEFINITIONS['channel']['id']
            hilbert_sub_cell.shapes(layer_id).insert(hilbert_region)
            
            # Calculate position
            x = start_x + i * cell_spacing_x
            y = start_y + 3 * cell_spacing_y
            
            # Insert into scan cell
            hilbert_scan_cell.insert(pya.CellInstArray(
                hilbert_sub_cell.cell_index(), 
                pya.Trans(pya.Point(int(x), int(y)))
            ))
        
        # Insert Hilbert parameter scan into top level, positioned to the right of Serpentine test
        top_cell.insert(pya.CellInstArray(
            hilbert_scan_cell.cell_index(), 
            pya.Trans(pya.Point(1000, 0))
        ))
        
        print("✓ Hilbert parameter scan test generated successfully")
        
    except Exception as e:
        print(f"✗ Hilbert parameter scan test generation failed: {e}")
        return
    
    # ===== Save results =====
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from config import get_gds_path
    
    output_file = get_gds_path("TEST_MEANDER.gds")
    print(f"Saving to: {output_file}")
    try:
        meander.layout.write(output_file)
        print("✓ Save successful")
    except Exception as e:
        print(f"✗ Save failed: {e}")
        return
    
    print("=== Complete ===")
    print("Contains structures:")
    print("  - Test_All_Curves")
    print("    - Hilbert_Test")
    print("    - Serpentine_Test")
    print("    - Peano_Test")
    print("    - Gosper_Test")
    print("    - Moore_Test")
    print("    - Hilbert_Parameter_Scan")
    print("      - Row 1: Different orders (3, 4, 5, 6)")
    print("      - Row 2: Different step sizes (8, 10, 12, 15 μm)")
    print("      - Row 3: Different line widths (2, 3, 4, 5 μm)")
    print("      - Row 4: Different margins (1, 2, 3 μm)")


if __name__ == "__main__":
    main()