#!/usr/bin/env python3
"""
Greyscale Microlens Generator
Creates single-channel 8-bit images with spherical/parabolic microlens profile for grayscale lithography.
The grayscale values represent the height profile of the microlens.
"""

import numpy as np
from PIL import Image
import os
import math

# =============================================================================
# PARAMETERS
# =============================================================================

# Canvas dimensions
WIDTH = 1024
HEIGHT = 1024

# Microlens parameters
CX = WIDTH // 2
CY = HEIGHT // 2  # Center of image
# Radius to fill entire image (to corners)
RADIUS = math.sqrt((WIDTH/2)**2 + (HEIGHT/2)**2)

# Lens profile type
LENS_TYPE = "spherical"  # Options: "spherical", "parabolic"
FOCAL_LENGTH = 1000  # Focal length in pixels (for parabolic lens)

# Height mapping parameters
MAX_HEIGHT = 1.0  # Maximum height (normalized, will be mapped to 255)
MIN_HEIGHT = 0.0  # Minimum height (normalized, will be mapped to 0)
HEIGHT_MAPPING = "linear"  # Options: "linear", "quadratic", "sqrt"

# Background and lens parameters
BACKGROUND_GRAY = 0
LENS_OUTSIDE_GRAY = 0

# Border parameters
BORDER_WIDTH = 10  # Unified border width for lens and colorbar
BORDER_GRAY = 255

# Corner mark parameters
CORNER_MARK_SIZE = 50  # Size of L-shaped corner marks
CORNER_MARK_THICKNESS = 10  # Thickness of corner mark lines
CORNER_MARK_GRAY = 255  # Color of corner marks
CORNER_MARK_OFFSET = 0  # No offset - marks at exact corners

# Output filename (in same directory as script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PNG_FILENAME = os.path.join(SCRIPT_DIR, "greyscale_microlens_1024.png")

# =============================================================================
# FUNCTIONS
# =============================================================================

def calculate_spherical_height(r, R, max_height=1.0):
    """
    Calculate height for spherical lens profile.
    
    Args:
        r: Distance from center
        R: Aperture radius
        max_height: Maximum height (normalized)
        
    Returns:
        float: Normalized height [0, max_height]
    """
    if r >= R:
        return 0.0
    
    # Spherical cap height: h = R - sqrt(R^2 - r^2)
    # For a lens, we use sag formula: h = R - sqrt(R^2 - r^2)
    # We normalize so that h(R) = 0 and h(0) = max_height
    # Using radius of curvature R_curv = R^2 / (2*max_height) for small sag
    if R == 0:
        return max_height if r == 0 else 0.0
    
    # Simplified: use parabolic approximation for small sag
    # h = max_height * (1 - (r/R)^2)
    height = max_height * (1.0 - (r / R) ** 2)
    return max(0.0, height)

def calculate_parabolic_height(r, R, focal_length, max_height=1.0):
    """
    Calculate height for parabolic lens profile.
    
    Args:
        r: Distance from center
        R: Aperture radius
        focal_length: Focal length
        max_height: Maximum height (normalized)
        
    Returns:
        float: Normalized height [0, max_height]
    """
    if r >= R:
        return 0.0
    
    # Parabolic profile: h = r^2 / (4*f)
    # Normalize so that h(R) = 0 and h(0) = max_height
    if focal_length <= 0:
        return calculate_spherical_height(r, R, max_height)
    
    # Calculate actual height
    h_actual = (r ** 2) / (4.0 * focal_length)
    h_max_actual = (R ** 2) / (4.0 * focal_length)
    
    # Normalize to [0, max_height]
    if h_max_actual > 0:
        height = max_height * (1.0 - h_actual / h_max_actual)
    else:
        height = max_height if r == 0 else 0.0
    
    return max(0.0, height)

def map_height_to_grayscale(height, min_height=0.0, max_height=1.0, mapping="linear"):
    """
    Map normalized height to grayscale value [0, 255].
    
    Args:
        height: Normalized height [0, 1]
        min_height: Minimum height value
        max_height: Maximum height value
        mapping: Mapping function type
        
    Returns:
        int: Grayscale value [0, 255]
    """
    # Normalize height to [0, 1]
    if max_height > min_height:
        normalized = (height - min_height) / (max_height - min_height)
    else:
        normalized = 1.0 if height > 0 else 0.0
    
    normalized = max(0.0, min(1.0, normalized))
    
    # Apply mapping function
    if mapping == "linear":
        mapped = normalized
    elif mapping == "quadratic":
        mapped = normalized ** 2
    elif mapping == "sqrt":
        mapped = math.sqrt(normalized)
    else:
        mapped = normalized
    
    # Convert to grayscale [0, 255]
    grayscale = int(round(mapped * 255))
    return max(0, min(255, grayscale))

def generate_microlens_image(width, height, cx, cy, radius, lens_type="spherical", 
                             focal_length=1000, max_height=1.0, min_height=0.0,
                             height_mapping="linear", background_gray=0, lens_outside_gray=0):
    """
    Generate a single-channel 8-bit image with microlens height profile.
    
    Args:
        width, height: Canvas dimensions
        cx, cy: Lens center coordinates
        radius: Aperture radius
        lens_type: Type of lens profile ("spherical" or "parabolic")
        focal_length: Focal length for parabolic lens
        max_height: Maximum height (normalized)
        min_height: Minimum height (normalized)
        height_mapping: Height to grayscale mapping function
        background_gray: Background pixel value
        lens_outside_gray: Pixel value outside lens aperture
        
    Returns:
        np.ndarray: Single-channel uint8 image array
    """
    # Create coordinate grids
    y, x = np.ogrid[:height, :width]
    
    # Calculate distances from center
    dx = x - cx
    dy = y - cy
    distance = np.sqrt(dx**2 + dy**2)
    
    # Create lens mask
    lens_mask = distance <= radius
    
    # Calculate height profile
    if lens_type == "spherical":
        # Use vectorized calculation for spherical lens
        r_normalized = np.clip(distance / radius, 0, 1)
        heights = max_height * (1.0 - r_normalized ** 2)
        heights = np.clip(heights, 0, max_height)
    elif lens_type == "parabolic":
        # Use vectorized calculation for parabolic lens
        r_normalized = np.clip(distance / radius, 0, 1)
        # Parabolic: h = max_height * (1 - (r/R)^2)
        heights = max_height * (1.0 - r_normalized ** 2)
        heights = np.clip(heights, 0, max_height)
    else:
        # Default to spherical
        r_normalized = np.clip(distance / radius, 0, 1)
        heights = max_height * (1.0 - r_normalized ** 2)
        heights = np.clip(heights, 0, max_height)
    
    # Map heights to grayscale values
    # For grayscale lithography: white = exposure = thinner, black = thicker
    # So larger height (thicker) should map to smaller grayscale (darker)
    if height_mapping == "linear":
        normalized_heights = (heights - min_height) / (max_height - min_height) if max_height > min_height else heights
        normalized_heights = np.clip(normalized_heights, 0, 1)
        # Invert: larger height (thicker) -> smaller grayscale (darker)
        grayscale_values = np.round(255 - normalized_heights * 255).astype(np.uint8)
    elif height_mapping == "quadratic":
        normalized_heights = (heights - min_height) / (max_height - min_height) if max_height > min_height else heights
        normalized_heights = np.clip(normalized_heights, 0, 1)
        grayscale_values = np.round(255 - (normalized_heights ** 2) * 255).astype(np.uint8)
    elif height_mapping == "sqrt":
        normalized_heights = (heights - min_height) / (max_height - min_height) if max_height > min_height else heights
        normalized_heights = np.clip(normalized_heights, 0, 1)
        grayscale_values = np.round(255 - np.sqrt(normalized_heights) * 255).astype(np.uint8)
    else:
        normalized_heights = (heights - min_height) / (max_height - min_height) if max_height > min_height else heights
        normalized_heights = np.clip(normalized_heights, 0, 1)
        grayscale_values = np.round(255 - normalized_heights * 255).astype(np.uint8)
    
    # Initialize image with grayscale values (fill entire image)
    image = grayscale_values.copy()
    
    return image

def draw_lens_border(image, cx, cy, radius, border_width, border_gray):
    """
    Draw a white border around the lens aperture.
    
    Args:
        image: Image array to modify in-place
        cx, cy: Lens center coordinates
        radius: Aperture radius
        border_width: Width of the border
        border_gray: Pixel value for border
    """
    height, width = image.shape
    
    # Create coordinate grids
    y, x = np.ogrid[:height, :width]
    dx = x - cx
    dy = y - cy
    distance = np.sqrt(dx**2 + dy**2)
    
    # Create border mask (ring around the lens)
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

def save_image(image, png_filename):
    """
    Save image in PNG format.
    
    Args:
        image: Image array
        png_filename: PNG filename
    """
    # Convert to PIL Image
    pil_image = Image.fromarray(image, mode='L')
    
    # Save PNG file
    pil_image.save(png_filename, format='PNG')
    print(f"Saved PNG: {png_filename}")

def verify_image(image, cx, cy, radius):
    """
    Perform self-check verification of the generated image.
    
    Args:
        image: Generated image array
        cx, cy: Lens center coordinates
        radius: Aperture radius
    """
    print("\n=== SELF-CHECK VERIFICATION ===")
    
    # Check center value (should be maximum)
    center_value = image[cy, cx]
    print(f"Center value (should be max): {center_value}")
    
    # Check edge value (should be minimum or background)
    edge_x = int(cx + radius)
    edge_y = cy
    if 0 <= edge_x < image.shape[1] and 0 <= edge_y < image.shape[0]:
        edge_value = image[edge_y, edge_x]
        print(f"Edge value (at radius): {edge_value}")
    
    # Check values at different radii
    check_radii = [radius // 4, radius // 2, 3 * radius // 4]
    print("Grayscale values at different radii:")
    for r in check_radii:
        x = int(cx + r)
        y = cy
        if 0 <= x < image.shape[1] and 0 <= y < image.shape[0]:
            gray_value = image[y, x]
            print(f"  Radius {r} px: {gray_value}")
    
    # Print image statistics
    print(f"Image dtype: {image.dtype}")
    print(f"Image min: {image.min()}")
    print(f"Image max: {image.max()}")
    print(f"Image shape: {image.shape}")
    print(f"Lens type: {LENS_TYPE}")
    print(f"Height mapping: {HEIGHT_MAPPING}")

def main():
    """
    Main function to generate and save the greyscale microlens image.
    """
    print("Generating greyscale microlens image...")
    print(f"Lens type: {LENS_TYPE}")
    print(f"Height mapping: {HEIGHT_MAPPING}")
    
    # Generate the microlens image
    image = generate_microlens_image(
        width=WIDTH,
        height=HEIGHT,
        cx=CX,
        cy=CY,
        radius=RADIUS,
        lens_type=LENS_TYPE,
        focal_length=FOCAL_LENGTH,
        max_height=MAX_HEIGHT,
        min_height=MIN_HEIGHT,
        height_mapping=HEIGHT_MAPPING,
        background_gray=BACKGROUND_GRAY,
        lens_outside_gray=LENS_OUTSIDE_GRAY
    )
    
    # Save images
    save_image(image, PNG_FILENAME)
    
    # Perform self-check verification
    verify_image(image, CX, CY, RADIUS)
    
    print("\nGeneration complete!")

if __name__ == "__main__":
    main()
