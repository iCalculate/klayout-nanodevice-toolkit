#!/usr/bin/env python3
"""
Greyscale Hexagon Array Generator - Refactored
Creates single-channel 8-bit images with hexagonal close-packed array pattern for grayscale lithography.
Fixed geometry for true close-packing with flat-top hexagons.
"""

import numpy as np
from PIL import Image, ImageDraw
import os
import math

# =============================================================================
# PARAMETERS
# =============================================================================

# Canvas dimensions
WIDTH = 1024
HEIGHT = 1024

# Hexagon array parameters
HEXAGON_SIZE = 30  # Radius of each hexagon
SPACING = 0  # No spacing for proper tessellation
ARRAY_ROWS = 14  # Number of rows
ARRAY_COLS = 19  # Number of columns

# Background and hexagon parameters
BACKGROUND_GRAY = 0

# Gradient pattern parameters
GRADIENT_PATTERN = "random"  # Options: "snake_spiral", "snake_fold", "random", "uniform"
UNIFORM_GRAY = 255  # Color for uniform pattern
RANDOM_SEED = 42  # Seed for random pattern

# Border parameters
BORDER_WIDTH = 10  # Unified border width for hexagons and colorbar
BORDER_GRAY = 255

# Colorbar border parameters
COLORBAR_BORDER_WIDTH = 10  # Border width specifically for colorbar
COLORBAR_BORDER_GRAY = 255  # Border color for colorbar

# Corner mark parameters
CORNER_MARK_SIZE = 50  # Size of L-shaped corner marks
CORNER_MARK_THICKNESS = 10  # Thickness of corner mark lines
CORNER_MARK_GRAY = 255  # Color of corner marks
CORNER_MARK_OFFSET = 0  # No offset - marks at exact corners

# Hexagon array position parameters
ARRAY_OFFSET_X = 30  # Horizontal offset for hexagon array (0 = centered)
ARRAY_OFFSET_Y = -30  # Vertical offset for hexagon array (negative = move up)

# Colorbar parameters (horizontal at bottom)
COLORBAR_WIDTH = int(400 * 2.0)  # 200% wider (800 pixels)
COLORBAR_HEIGHT = int(100 * 0.7)  # 70% narrower (70 pixels)
COLORBAR_X = (WIDTH - COLORBAR_WIDTH) // 2  # Center horizontally
COLORBAR_Y = HEIGHT - COLORBAR_HEIGHT - 60  # Move up to balance with array

# Output format control
OUTPUT_FORMAT = "BMP"  # Options: "BMP", "TIFF", "BOTH"
OUTPUT_BOTH = False  # If True, save both formats regardless of OUTPUT_FORMAT

# Output filenames (using configured output directory)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config import get_image_path

TIFF_FILENAME = get_image_path("greyscale_hexagon_array_1024.tif")
BMP_FILENAME = get_image_path("greyscale_hexagon_array_1024.bmp")

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def hex_vertices_flat_top(cx, cy, R):
    """
    Calculate vertices of a flat-top hexagon.
    
    Args:
        cx, cy: Center coordinates
        R: Radius (center to vertex distance)
        
    Returns:
        List[Tuple[int,int]]: 6 vertices in clockwise order
    """
    # Flat-top hexagon: angles start from 0° (rightmost vertex)
    angles = [0, 60, 120, 180, 240, 300]  # degrees
    vertices = []
    
    for angle_deg in angles:
        angle_rad = math.radians(angle_deg)
        vx = cx + R * math.cos(angle_rad)
        vy = cy + R * math.sin(angle_rad)
        vertices.append((int(round(vx)), int(round(vy))))
    
    return vertices

def generate_centers_flat_top(W, H, hexagon_size, rows, cols, spacing=0, offset_x=0, offset_y=0):
    """
    Generate center coordinates for flat-top hexagonal close-packing.
    
    Args:
        W, H: Canvas dimensions
        hexagon_size: Hexagon radius
        rows, cols: Array dimensions
        spacing: Additional spacing on top of close-packing
        offset_x: Horizontal offset for array position
        offset_y: Vertical offset for array position
        
    Returns:
        List[Tuple[float, float]]: List of (cx, cy) center coordinates
    """
    # Flat-top hexagon dimensions
    hex_width = 2 * hexagon_size
    hex_height = math.sqrt(3) * hexagon_size
    
    # Close-packing step sizes for flat-top hexagons
    dx = 3/2 * hexagon_size  # Horizontal step between columns
    dy = math.sqrt(3) * hexagon_size  # Vertical step between rows
    
    # Add spacing
    dx += spacing
    dy += spacing
    
    centers = []
    
    # Generate all centers first
    for row in range(rows):
        for col in range(cols):
            # Base coordinates
            cx = col * dx
            cy = row * dy
            
            # Vertical offset for odd columns (key fix!)
            if col % 2 == 1:
                cy += hex_height / 2
            
            centers.append((cx, cy))
    
    # Calculate bounding box of all centers
    if not centers:
        return []
    
    centers_array = np.array(centers)
    min_x, min_y = centers_array.min(axis=0)
    max_x, max_y = centers_array.max(axis=0)
    
    # Add hexagon bounds to get total array bounds
    total_width = max_x - min_x + hex_width
    total_height = max_y - min_y + hex_height
    
    # Calculate offset to center the array
    center_offset_x = (W - total_width) / 2 - min_x
    center_offset_y = (H - total_height) / 2 - min_y
    
    # Apply centering offset plus user-specified offset
    final_centers = []
    for cx, cy in centers:
        final_x = cx + center_offset_x + offset_x
        final_y = cy + center_offset_y + offset_y
        final_centers.append((final_x, final_y))
    
    return final_centers

def calculate_gradient_values(rows, cols, pattern, random_seed=42):
    """
    Calculate gradient values for each hexagon in the array.
    
    Args:
        rows, cols: Array dimensions
        pattern: Gradient pattern type
        random_seed: Seed for random pattern
        
    Returns:
        np.ndarray: 2D array of grayscale values
    """
    if pattern == "uniform":
        return np.full((rows, cols), UNIFORM_GRAY, dtype=np.uint8)
    
    elif pattern == "random":
        np.random.seed(random_seed)
        return np.random.randint(0, 256, (rows, cols), dtype=np.uint8)
    
    elif pattern == "snake_spiral":
        # Snake spiral pattern: start from center, spiral outward
        values = np.zeros((rows, cols), dtype=np.uint8)
        center_row, center_col = rows // 2, cols // 2
        
        # Create spiral order
        spiral_order = []
        visited = np.zeros((rows, cols), dtype=bool)
        
        # Spiral outward from center
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # right, down, left, up
        direction = 0
        steps = 1
        r, c = center_row, center_col
        
        while len(spiral_order) < rows * cols:
            for _ in range(2):  # Each direction is used twice before increasing steps
                for _ in range(steps):
                    if 0 <= r < rows and 0 <= c < cols and not visited[r, c]:
                        spiral_order.append((r, c))
                        visited[r, c] = True
                    r += directions[direction][0]
                    c += directions[direction][1]
                direction = (direction + 1) % 4
            steps += 1
        
        # Assign gradient values
        for i, (r, c) in enumerate(spiral_order):
            values[r, c] = int((i / (rows * cols - 1)) * 255)
        
        return values
    
    elif pattern == "snake_fold":
        # Snake fold pattern: zigzag through rows
        values = np.zeros((rows, cols), dtype=np.uint8)
        
        for i in range(rows * cols):
            if i // cols % 2 == 0:  # Even rows: left to right
                row = i // cols
                col = i % cols
            else:  # Odd rows: right to left
                row = i // cols
                col = cols - 1 - (i % cols)
            
            values[row, col] = int((i / (rows * cols - 1)) * 255)
        
        return values
    
    else:
        # Default to uniform
        return np.full((rows, cols), UNIFORM_GRAY, dtype=np.uint8)

def draw_hex_array(image, centers, hexagon_size, values):
    """
    Draw hexagonal array using polygon filling.
    
    Args:
        image: PIL Image object to draw on
        centers: List of (cx, cy) center coordinates
        hexagon_size: Hexagon radius
        values: 2D array of grayscale values
    """
    draw = ImageDraw.Draw(image)
    
    # Flatten values array for indexing
    values_flat = values.flatten()
    
    for i, (cx, cy) in enumerate(centers):
        if i < len(values_flat):
            gray_value = int(values_flat[i])
            
            # Get hexagon vertices
            vertices = hex_vertices_flat_top(cx, cy, hexagon_size)
            
            # Draw filled hexagon
            draw.polygon(vertices, fill=gray_value)

def save_image(image, tiff_filename, bmp_filename, output_format="BMP", output_both=False):
    """
    Save image in specified format(s).
    
    Args:
        image: PIL Image object
        tiff_filename: TIFF filename
        bmp_filename: BMP filename
        output_format: Output format ("BMP", "TIFF", "BOTH")
        output_both: If True, save both formats regardless of output_format
    """
    # Convert to PIL Image
    if image.mode != 'L':
        image = image.convert('L')
    
    # Determine what to save
    save_tiff = (output_format == "TIFF" or output_format == "BOTH" or output_both)
    save_bmp = (output_format == "BMP" or output_format == "BOTH" or output_both)
    
    # Save files
    if save_tiff:
        image.save(tiff_filename, format='TIFF')
        print(f"Saved TIFF: {tiff_filename}")
    
    if save_bmp:
        image.save(bmp_filename, format='BMP')
        print(f"Saved BMP: {bmp_filename}")

# =============================================================================
# OPTIONAL FEATURES (only used if enabled)
# =============================================================================

def draw_corner_marks(image, width, height, mark_size, thickness, gray_value, offset):
    """Draw L-shaped corner marks at all four corners."""
    # Draw each corner mark individually
    draw_l_mark(image, offset, offset, mark_size, thickness, gray_value, 1, 1)
    draw_l_mark(image, width - 1 - offset, offset, mark_size, thickness, gray_value, -1, 1)
    draw_l_mark(image, offset, height - 1 - offset, mark_size, thickness, gray_value, 1, -1)
    draw_l_mark(image, width - 1 - offset, height - 1 - offset, mark_size, thickness, gray_value, -1, -1)

def draw_l_mark(image, start_x, start_y, size, thickness, gray_value, h_dir, v_dir):
    """Draw a single L-shaped mark."""
    width, height = image.size
    
    # Calculate end points
    end_x = start_x + h_dir * size
    end_y = start_y + v_dir * size
    
    # Draw horizontal line
    for x in range(min(start_x, end_x), max(start_x, end_x) + 1):
        for dy in range(-thickness//2, thickness//2 + 1):
            y = start_y + dy
            if 0 <= x < width and 0 <= y < height:
                image.putpixel((x, y), gray_value)
    
    # Draw vertical line
    for y in range(min(start_y, end_y), max(start_y, end_y) + 1):
        for dx in range(-thickness//2, thickness//2 + 1):
            x = start_x + dx
            if 0 <= x < width and 0 <= y < height:
                image.putpixel((x, y), gray_value)

def draw_colorbar(image, x, y, width, height):
    """Draw a horizontal colorbar."""
    # Create horizontal gradient from 0 to 255
    for j in range(width):
        gray_value = int((j / (width - 1)) * 255)
        for i in range(height):
            if 0 <= x + j < image.size[0] and 0 <= y + i < image.size[1]:
                image.putpixel((x + j, y + i), gray_value)
    
    # Add border around colorbar using colorbar-specific border parameters
    border_gray = COLORBAR_BORDER_GRAY
    border_width = COLORBAR_BORDER_WIDTH
    
    # Draw border with specified width
    for bw in range(border_width):
        # Top and bottom borders
        for j in range(width + 2 * bw):
            if 0 <= x - bw + j < image.size[0]:
                if 0 <= y - bw < image.size[1]:
                    image.putpixel((x - bw + j, y - bw), border_gray)
                if 0 <= y + height + bw - 1 < image.size[1]:
                    image.putpixel((x - bw + j, y + height + bw - 1), border_gray)
        
        # Left and right borders
        for i in range(height + 2 * bw):
            if 0 <= y - bw + i < image.size[1]:
                if 0 <= x - bw < image.size[0]:
                    image.putpixel((x - bw, y - bw + i), border_gray)
                if 0 <= x + width + bw - 1 < image.size[0]:
                    image.putpixel((x + width + bw - 1, y - bw + i), border_gray)

# =============================================================================
# VERIFICATION FUNCTIONS
# =============================================================================

def verify_close_packing(centers, hexagon_size):
    """
    Verify close-packing relationships.
    
    Args:
        centers: List of center coordinates
        hexagon_size: Hexagon radius
        
    Returns:
        dict: Verification results
    """
    if len(centers) < 2:
        return {"error": "Not enough centers for verification"}
    
    centers_array = np.array(centers)
    distances = []
    
    # Calculate distances to nearest neighbors
    for i, center in enumerate(centers_array):
        others = np.delete(centers_array, i, axis=0)
        distances_to_others = np.sqrt(np.sum((others - center)**2, axis=1))
        min_distance = np.min(distances_to_others)
        distances.append(min_distance)
    
    distances = np.array(distances)
    
    # Expected distances for flat-top close-packing
    expected_horizontal = 3/2 * hexagon_size  # Horizontal neighbors
    expected_diagonal = math.sqrt((3/2 * hexagon_size)**2 + (math.sqrt(3)/2 * hexagon_size)**2)  # Diagonal neighbors
    
    return {
        "mean_distance": np.mean(distances),
        "std_distance": np.std(distances),
        "expected_horizontal": expected_horizontal,
        "expected_diagonal": expected_diagonal,
        "distances": distances
    }

def verify_image_properties(image):
    """
    Verify image properties and statistics.
    
    Args:
        image: PIL Image object
        
    Returns:
        dict: Image properties
    """
    # Convert to numpy array for analysis
    img_array = np.array(image)
    
    # Calculate background pixel ratio
    background_pixels = np.sum(img_array == BACKGROUND_GRAY)
    total_pixels = img_array.size
    background_ratio = background_pixels / total_pixels
    
    return {
        "dtype": str(img_array.dtype),
        "min_value": int(img_array.min()),
        "max_value": int(img_array.max()),
        "shape": img_array.shape,
        "background_ratio": background_ratio,
        "mode": image.mode
    }

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """
    Main function to generate and save the greyscale hexagon array image.
    """
    print("Generating greyscale hexagon array image...")
    
    # Generate center coordinates
    centers = generate_centers_flat_top(WIDTH, HEIGHT, HEXAGON_SIZE, ARRAY_ROWS, ARRAY_COLS, SPACING, ARRAY_OFFSET_X, ARRAY_OFFSET_Y)
    print(f"Generated {len(centers)} hexagon centers")
    
    # Calculate gradient values
    gradient_values = calculate_gradient_values(ARRAY_ROWS, ARRAY_COLS, GRADIENT_PATTERN, RANDOM_SEED)
    
    # Create image
    image = Image.new('L', (WIDTH, HEIGHT), BACKGROUND_GRAY)
    
    # Draw hexagon array
    draw_hex_array(image, centers, HEXAGON_SIZE, gradient_values)
    
    # Draw corner marks
    draw_corner_marks(image, WIDTH, HEIGHT, CORNER_MARK_SIZE, CORNER_MARK_THICKNESS, 
                     CORNER_MARK_GRAY, CORNER_MARK_OFFSET)
    
    # Draw colorbar
    draw_colorbar(image, COLORBAR_X, COLORBAR_Y, COLORBAR_WIDTH, COLORBAR_HEIGHT)
    
    # Save images
    save_image(image, TIFF_FILENAME, BMP_FILENAME, OUTPUT_FORMAT, OUTPUT_BOTH)
    
    # Perform verification
    print("\n=== SELF-CHECK VERIFICATION ===")
    
    # Verify close-packing
    packing_results = verify_close_packing(centers, HEXAGON_SIZE)
    if "error" not in packing_results:
        print(f"Close-packing verification:")
        print(f"  Mean nearest neighbor distance: {packing_results['mean_distance']:.2f} px")
        print(f"  Std nearest neighbor distance: {packing_results['std_distance']:.2f} px")
        print(f"  Expected horizontal distance: {packing_results['expected_horizontal']:.2f} px")
        print(f"  Expected diagonal distance: {packing_results['expected_diagonal']:.2f} px")
    
    # Verify image properties
    img_props = verify_image_properties(image)
    print(f"Image properties:")
    print(f"  Dtype: {img_props['dtype']}")
    print(f"  Min value: {img_props['min_value']}")
    print(f"  Max value: {img_props['max_value']}")
    print(f"  Shape: {img_props['shape']}")
    print(f"  Background ratio: {img_props['background_ratio']:.3f}")
    print(f"  Mode: {img_props['mode']}")
    
    # Visual check information
    print(f"\nVisual check:")
    print(f"  R={HEXAGON_SIZE}, rows={ARRAY_ROWS}, cols={ARRAY_COLS}")
    print(f"  Odd columns should be vertically offset by {math.sqrt(3)/2*HEXAGON_SIZE:.1f} px")
    print(f"  Check 3 random columns for proper vertical offset")
    
    print("\nGeneration complete!")

if __name__ == "__main__":
    main()