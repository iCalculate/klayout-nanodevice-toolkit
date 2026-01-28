#!/usr/bin/env python3
"""
Greyscale Angular Circle Generator
Creates single-channel 8-bit images with angular gradient and tick marks for grayscale lithography.
"""

import numpy as np
from PIL import Image
import os

# =============================================================================
# PARAMETERS
# =============================================================================

# Canvas dimensions
WIDTH = 1024
HEIGHT = 1024

# Circle parameters
CX = WIDTH // 2
CY = HEIGHT // 2 - 80  # Move circle up to balance with colorbar
RADIUS = 400

# Background and circle parameters
BACKGROUND_GRAY = 0
CIRCLE_OUTSIDE_GRAY = 0

# Border parameters
BORDER_WIDTH = 10  # Unified border width for circle and colorbar
BORDER_GRAY = 255

# Corner mark parameters
CORNER_MARK_SIZE = 50  # Size of L-shaped corner marks
CORNER_MARK_THICKNESS = 10  # Thickness of corner mark lines (doubled)
CORNER_MARK_GRAY = 255  # Color of corner marks
CORNER_MARK_OFFSET = 0  # No offset - marks at exact corners

# Tick mark parameters
TICK_ANGLES = [0, 60, 120, 180, 240, 300]  # degrees
TICK_LENGTH = 20
TICK_THICKNESS = 20  # Made thicker
TICK_GRAY = 255

# Colorbar parameters (horizontal at bottom)
COLORBAR_WIDTH = int(400 * 2.0)  # 200% wider (800 pixels)
COLORBAR_HEIGHT = int(100 * 0.7)  # 70% narrower (70 pixels)
COLORBAR_X = (WIDTH - COLORBAR_WIDTH) // 2  # Center horizontally
COLORBAR_Y = HEIGHT - COLORBAR_HEIGHT - 60  # Move up to balance with circle

# Output format control
OUTPUT_FORMAT = "BMP"  # Options: "BMP", "TIFF", "BOTH"
OUTPUT_BOTH = False  # If True, save both formats regardless of OUTPUT_FORMAT

# Output filenames (using configured output directory)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config import get_image_path

TIFF_FILENAME = get_image_path("greyscale_angular_circle_1024.tif")
BMP_FILENAME = get_image_path("greyscale_angular_circle_1024.bmp")

# =============================================================================
# FUNCTIONS
# =============================================================================

def generate_gradient_image(width, height, cx, cy, radius, background_gray=0, circle_outside_gray=0):
    """
    Generate a single-channel 8-bit image with angular gradient.
    
    Args:
        width, height: Canvas dimensions
        cx, cy: Circle center coordinates
        radius: Circle radius
        background_gray: Background pixel value
        circle_outside_gray: Pixel value outside circle
        
    Returns:
        np.ndarray: Single-channel uint8 image array
    """
    # Create coordinate grids
    y, x = np.ogrid[:height, :width]
    
    # Calculate distances from center
    dx = x - cx
    dy = y - cy
    distance = np.sqrt(dx**2 + dy**2)
    
    # Create circle mask
    circle_mask = distance <= radius
    
    # Calculate angles (atan2 gives [-π, π], convert to [0, 360) degrees)
    angles_rad = np.arctan2(dy, dx)
    angles_deg = np.degrees(angles_rad)
    angles_deg = np.where(angles_deg < 0, angles_deg + 360, angles_deg)
    
    # Map angles to grayscale values [0, 255]
    grayscale_values = np.round((angles_deg / 360.0) * 255).astype(np.uint8)
    
    # Initialize image with background
    image = np.full((height, width), background_gray, dtype=np.uint8)
    
    # Apply circle mask and gradient
    image[circle_mask] = grayscale_values[circle_mask]
    
    # Set area outside circle
    image[~circle_mask] = circle_outside_gray
    
    return image

def draw_circle_border(image, cx, cy, radius, border_width, border_gray):
    """
    Draw a white border around the circle.
    
    Args:
        image: Image array to modify in-place
        cx, cy: Circle center coordinates
        radius: Circle radius
        border_width: Width of the border
        border_gray: Pixel value for border
    """
    height, width = image.shape
    
    # Create coordinate grids
    y, x = np.ogrid[:height, :width]
    dx = x - cx
    dy = y - cy
    distance = np.sqrt(dx**2 + dy**2)
    
    # Create border mask (ring around the circle)
    outer_mask = distance <= radius + border_width
    inner_mask = distance <= radius
    border_mask = outer_mask & ~inner_mask
    
    # Apply border
    image[border_mask] = border_gray

def draw_corner_marks(image, width, height, mark_size, thickness, gray_value, offset):
    """
    Draw L-shaped corner marks at all four corners with uniform width.
    
    Args:
        image: Image array to modify in-place
        width, height: Image dimensions
        mark_size: Size of the L-shaped marks
        thickness: Thickness of the mark lines
        gray_value: Pixel value for marks
        offset: Distance from image edges
    """
    # Draw each corner mark individually for better control
    # Top-left corner: L pointing right and down
    draw_l_mark(image, offset, offset, mark_size, thickness, gray_value, 1, 1)
    
    # Top-right corner: L pointing left and down
    draw_l_mark(image, width - 1 - offset, offset, mark_size, thickness, gray_value, -1, 1)
    
    # Bottom-left corner: L pointing right and up
    draw_l_mark(image, offset, height - 1 - offset, mark_size, thickness, gray_value, 1, -1)
    
    # Bottom-right corner: L pointing left and up
    draw_l_mark(image, width - 1 - offset, height - 1 - offset, mark_size, thickness, gray_value, -1, -1)

def draw_l_mark(image, start_x, start_y, size, thickness, gray_value, h_dir, v_dir):
    """
    Draw a single L-shaped mark with consistent width.
    
    Args:
        image: Image array to modify in-place
        start_x, start_y: Starting coordinates
        size: Size of the L-shape
        thickness: Thickness of the lines
        gray_value: Pixel value for the mark
        h_dir: Horizontal direction (1 for right, -1 for left)
        v_dir: Vertical direction (1 for down, -1 for up)
    """
    height, width = image.shape
    
    # Calculate end points
    end_x = start_x + h_dir * size
    end_y = start_y + v_dir * size
    
    # Draw horizontal line with proper thickness
    for x in range(min(start_x, end_x), max(start_x, end_x) + 1):
        for dy in range(-thickness//2, thickness//2 + 1):
            y = start_y + dy
            if 0 <= x < width and 0 <= y < height:
                image[y, x] = gray_value
    
    # Draw vertical line with proper thickness
    for y in range(min(start_y, end_y), max(start_y, end_y) + 1):
        for dx in range(-thickness//2, thickness//2 + 1):
            x = start_x + dx
            if 0 <= x < width and 0 <= y < height:
                image[y, x] = gray_value

def draw_tick_marks(image, cx, cy, radius, tick_angles, tick_length, tick_thickness, tick_gray):
    """
    Draw tick marks on the image in-place.
    
    Args:
        image: Image array to modify in-place
        cx, cy: Circle center coordinates
        radius: Circle radius
        tick_angles: List of angles in degrees
        tick_length: Length of tick marks
        tick_thickness: Thickness of tick marks
        tick_gray: Pixel value for tick marks
    """
    height, width = image.shape
    
    for angle_deg in tick_angles:
        # Convert angle to radians
        angle_rad = np.radians(angle_deg)
        
        # Calculate unit direction vector
        ux = np.cos(angle_rad)
        uy = np.sin(angle_rad)
        
        # Generate points along the tick mark
        tick_points = []
        
        # Sample points from (R - tick_length) to R
        for t in np.linspace(radius - tick_length, radius, max(tick_length, 1)):
            x = int(cx + t * ux)
            y = int(cy + t * uy)
            
            # Check bounds
            if 0 <= x < width and 0 <= y < height:
                tick_points.append((x, y))
        
        # Apply thickness using morphological dilation approach
        for x, y in tick_points:
            # Draw thick line by filling neighborhood
            for dx in range(-tick_thickness//2, tick_thickness//2 + 1):
                for dy in range(-tick_thickness//2, tick_thickness//2 + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        # Check if point is within thickness distance
                        if dx*dx + dy*dy <= (tick_thickness//2)**2:
                            image[ny, nx] = tick_gray

def draw_colorbar(image, x, y, width, height):
    """
    Draw a horizontal colorbar showing angle-grayscale relationship.
    
    Args:
        image: Image array to modify in-place
        x, y: Top-left corner of colorbar
        width, height: Colorbar dimensions
    """
    # Create horizontal gradient from 0 to 255
    for j in range(width):
        # Map horizontal position to grayscale value (0 at left, 255 at right)
        gray_value = int((j / (width - 1)) * 255)
        
        # Fill the colorbar row
        for i in range(height):
            if 0 <= x + j < image.shape[1] and 0 <= y + i < image.shape[0]:
                image[y + i, x + j] = gray_value
    
    # Add border around colorbar using unified border width
    border_gray = 255
    border_width = BORDER_WIDTH
    
    # Draw border with specified width
    for bw in range(border_width):
        # Top and bottom borders
        for j in range(width + 2 * bw):
            if 0 <= x - bw + j < image.shape[1]:
                if 0 <= y - bw < image.shape[0]:
                    image[y - bw, x - bw + j] = border_gray
                if 0 <= y + height + bw - 1 < image.shape[0]:
                    image[y + height + bw - 1, x - bw + j] = border_gray
        
        # Left and right borders
        for i in range(height + 2 * bw):
            if 0 <= y - bw + i < image.shape[0]:
                if 0 <= x - bw < image.shape[1]:
                    image[y - bw + i, x - bw] = border_gray
                if 0 <= x + width + bw - 1 < image.shape[1]:
                    image[y - bw + i, x + width + bw - 1] = border_gray

def save_image(image, tiff_filename, bmp_filename, output_format="BMP", output_both=False):
    """
    Save image in specified format(s).
    
    Args:
        image: Image array
        tiff_filename: TIFF filename
        bmp_filename: BMP filename
        output_format: Output format ("BMP", "TIFF", "BOTH")
        output_both: If True, save both formats regardless of output_format
    """
    # Convert to PIL Image
    pil_image = Image.fromarray(image, mode='L')
    
    # Determine what to save
    save_tiff = (output_format == "TIFF" or output_format == "BOTH" or output_both)
    save_bmp = (output_format == "BMP" or output_format == "BOTH" or output_both)
    
    # Save files
    if save_tiff:
        pil_image.save(tiff_filename, format='TIFF')
        print(f"Saved TIFF: {tiff_filename}")
    
    if save_bmp:
        pil_image.save(bmp_filename, format='BMP')
        print(f"Saved BMP: {bmp_filename}")

def verify_image(image, cx, cy, radius):
    """
    Perform self-check verification of the generated image.
    
    Args:
        image: Generated image array
        cx, cy: Circle center coordinates
        radius: Circle radius
    """
    print("\n=== SELF-CHECK VERIFICATION ===")
    
    # Check four directions at R//2 distance
    check_radius = radius // 2
    directions = [
        (0, "0°"),
        (90, "90°"),
        (180, "180°"),
        (270, "270°")
    ]
    
    print("Grayscale values at R//2 in four directions:")
    for angle_deg, label in directions:
        angle_rad = np.radians(angle_deg)
        x = int(cx + check_radius * np.cos(angle_rad))
        y = int(cy + check_radius * np.sin(angle_rad))
        
        if 0 <= x < image.shape[1] and 0 <= y < image.shape[0]:
            gray_value = image[y, x]
            print(f"  {label}: {gray_value}")
        else:
            print(f"  {label}: Out of bounds")
    
    # Check tick mark at 0° (should be 255)
    angle_rad = np.radians(0)
    x = int(cx + radius * np.cos(angle_rad))
    y = int(cy + radius * np.sin(angle_rad))
    
    if 0 <= x < image.shape[1] and 0 <= y < image.shape[0]:
        tick_value = image[y, x]
        print(f"Tick mark at 0°: {tick_value}")
    else:
        print("Tick mark at 0°: Out of bounds")
    
    # Print image statistics
    print(f"Image dtype: {image.dtype}")
    print(f"Image min: {image.min()}")
    print(f"Image max: {image.max()}")
    print(f"Image shape: {image.shape}")

def main():
    """
    Main function to generate and save the greyscale angular circle image.
    """
    print("Generating greyscale angular circle image...")
    
    # Generate the gradient image
    image = generate_gradient_image(
        width=WIDTH,
        height=HEIGHT,
        cx=CX,
        cy=CY,
        radius=RADIUS,
        background_gray=BACKGROUND_GRAY,
        circle_outside_gray=CIRCLE_OUTSIDE_GRAY
    )
    
    # Draw circle border
    draw_circle_border(
        image=image,
        cx=CX,
        cy=CY,
        radius=RADIUS,
        border_width=BORDER_WIDTH,
        border_gray=BORDER_GRAY
    )
    
    # Draw tick marks
    draw_tick_marks(
        image=image,
        cx=CX,
        cy=CY,
        radius=RADIUS,
        tick_angles=TICK_ANGLES,
        tick_length=TICK_LENGTH,
        tick_thickness=TICK_THICKNESS,
        tick_gray=TICK_GRAY
    )
    
    # Draw colorbar
    draw_colorbar(
        image=image,
        x=COLORBAR_X,
        y=COLORBAR_Y,
        width=COLORBAR_WIDTH,
        height=COLORBAR_HEIGHT
    )
    
    # Draw corner marks
    draw_corner_marks(
        image=image,
        width=WIDTH,
        height=HEIGHT,
        mark_size=CORNER_MARK_SIZE,
        thickness=CORNER_MARK_THICKNESS,
        gray_value=CORNER_MARK_GRAY,
        offset=CORNER_MARK_OFFSET
    )
    
    # Save images
    save_image(image, TIFF_FILENAME, BMP_FILENAME, OUTPUT_FORMAT, OUTPUT_BOTH)
    
    # Perform self-check verification
    verify_image(image, CX, CY, RADIUS)
    
    print("\nGeneration complete!")

# =============================================================================
# OPTIONAL EXTENSIONS (commented out)
# =============================================================================

# def apply_lut(image, lut_array):
#     """
#     Apply lookup table transformation to image.
#     Args:
#         image: Input image array
#         lut_array: Lookup table array of length 256
#     Returns:
#         Transformed image array
#     """
#     return lut_array[image]

# def load_external_lut(filename):
#     """
#     Load external lookup table from file.
#     Args:
#         filename: Path to LUT file
#     Returns:
#         LUT array
#     """
#     # Implementation for loading external LUT
#     pass

if __name__ == "__main__":
    main()
