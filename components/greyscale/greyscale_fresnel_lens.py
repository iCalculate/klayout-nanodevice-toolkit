#!/usr/bin/env python3
"""
Greyscale Fresnel Lens Generator
Creates single-channel 8-bit images with Fresnel lens zone pattern for grayscale lithography.
The grayscale values represent the phase/height profile of the Fresnel lens zones.
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

# Fresnel lens parameters
CX = WIDTH // 2
CY = HEIGHT // 2  # Center of image
# Maximum radius to fill entire image (to corners)
MAX_RADIUS = math.sqrt((WIDTH/2)**2 + (HEIGHT/2)**2)

# Lens parameters
FOCAL_LENGTH = 1000  # Focal length in pixels (not used for continuous mode)
WAVELENGTH = 633  # Wavelength in nanometers (not used for continuous mode)
NUM_ZONES = 8  # Number of Fresnel zones - controls ring count

# Zone pattern type
ZONE_TYPE = "continuous"  # Options: "continuous", "blazed"
# For "continuous": continuous grayscale gradient based on phase
# For "blazed": sawtooth profile within each zone

# Phase mapping parameters
PHASE_MAPPING = "linear"  # Options: "linear", "quadratic", "sqrt"
INVERT_PHASE = False  # If True, invert the phase (black becomes white)

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
PNG_FILENAME = os.path.join(SCRIPT_DIR, "greyscale_fresnel_lens_1024.png")

# =============================================================================
# FUNCTIONS
# =============================================================================

def calculate_zone_radius(n, focal_length, wavelength):
    """
    Calculate the radius of the nth Fresnel zone.
    
    Args:
        n: Zone number (0, 1, 2, ...)
        focal_length: Focal length in pixels
        wavelength: Wavelength in nanometers
        
    Returns:
        float: Zone radius in pixels
    """
    # Fresnel zone radius: r_n = sqrt(n * lambda * f)
    # For normalized calculation, we use: r_n = sqrt(n * f_norm)
    # where f_norm is normalized focal length
    if n <= 0:
        return 0.0
    
    # Normalize wavelength to pixel scale (assuming 1 pixel = 1 nm for calculation)
    # Adjust this based on your actual pixel scale
    lambda_pixels = wavelength / 1000.0  # Convert nm to microns, then scale
    
    # Calculate zone radius
    radius = math.sqrt(n * lambda_pixels * focal_length)
    return radius

def calculate_fresnel_phase(r, focal_length, wavelength):
    """
    Calculate the phase at radius r for a Fresnel lens.
    
    Args:
        r: Distance from center
        focal_length: Focal length in pixels
        wavelength: Wavelength in nanometers
        
    Returns:
        float: Phase value [0, 2*pi]
    """
    # Phase = (2*pi / lambda) * (r^2 / (2*f))
    # Normalized: phase = (r^2 / (2*f)) * (2*pi / lambda_norm)
    if focal_length <= 0:
        return 0.0
    
    lambda_pixels = wavelength / 1000.0  # Convert nm to microns, then scale
    phase = (r ** 2) / (2.0 * focal_length) * (2.0 * math.pi / lambda_pixels)
    
    # Normalize to [0, 2*pi]
    phase = phase % (2.0 * math.pi)
    return phase

def calculate_zone_number(r, max_radius, num_zones):
    """
    Calculate which Fresnel zone a point at radius r belongs to.
    
    Args:
        r: Distance from center
        max_radius: Maximum radius of the lens
        num_zones: Number of zones
        
    Returns:
        int: Zone number [0, num_zones-1]
    """
    if r >= max_radius:
        return num_zones
    
    # Zones are equally spaced in radius squared
    # r_n^2 = (n / num_zones) * max_radius^2
    normalized_r_sq = (r / max_radius) ** 2
    zone = int(normalized_r_sq * num_zones)
    
    return min(zone, num_zones - 1)

def map_phase_to_grayscale(phase, zone_type="binary", invert=False):
    """
    Map phase value to grayscale value [0, 255].
    
    Args:
        phase: Phase value [0, 2*pi]
        zone_type: Type of zone pattern
        invert: Whether to invert the phase
        
    Returns:
        int: Grayscale value [0, 255]
    """
    if zone_type == "binary":
        # Binary zones: 0 or 255 based on zone number
        # Use phase to determine zone (even/odd)
        zone_phase = phase / (2.0 * math.pi)
        zone_num = int(zone_phase * NUM_ZONES) % 2
        grayscale = 255 if zone_num == 0 else 0
    elif zone_type == "blazed":
        # Blazed zones: sawtooth profile
        normalized_phase = (phase % (2.0 * math.pi)) / (2.0 * math.pi)
        grayscale = int(round(normalized_phase * 255))
    elif zone_type == "smooth":
        # Smooth transition: cosine profile
        normalized_phase = (phase % (2.0 * math.pi)) / (2.0 * math.pi)
        # Use cosine for smooth transition
        grayscale = int(round((0.5 + 0.5 * math.cos(2.0 * math.pi * normalized_phase)) * 255))
    else:
        # Default to binary
        zone_phase = phase / (2.0 * math.pi)
        zone_num = int(zone_phase * NUM_ZONES) % 2
        grayscale = 255 if zone_num == 0 else 0
    
    if invert:
        grayscale = 255 - grayscale
    
    return max(0, min(255, grayscale))

def generate_fresnel_lens_image(width, height, cx, cy, max_radius, focal_length, 
                               wavelength, num_zones, zone_type="binary",
                               phase_mapping="linear", invert_phase=False,
                               background_gray=0, lens_outside_gray=0):
    """
    Generate a single-channel 8-bit image with Fresnel lens zone pattern.
    
    Args:
        width, height: Canvas dimensions
        cx, cy: Lens center coordinates
        max_radius: Maximum radius of the lens
        focal_length: Focal length in pixels
        wavelength: Wavelength in nanometers
        num_zones: Number of Fresnel zones
        zone_type: Type of zone pattern
        phase_mapping: Phase mapping function (not used for binary zones)
        invert_phase: Whether to invert the phase
        background_gray: Background pixel value
        lens_outside_gray: Pixel value outside lens
        
    Returns:
        np.ndarray: Single-channel uint8 image array
    """
    # Create coordinate grids
    y, x = np.ogrid[:height, :width]
    
    # Calculate distances from center
    dx = x - cx
    dy = y - cy
    distance = np.sqrt(dx**2 + dy**2)
    
    # Calculate phase-based grayscale values for entire image
    if zone_type == "continuous":
        # Continuous grayscale based on phase delay for Fresnel convex lens
        # For convex lens: center is thickest (max phase), edge is thinnest (min phase)
        # For grayscale lithography: white = exposure = thinner, black = thicker
        # So larger phase delay (thicker) should map to smaller grayscale (darker)
        
        # Normalize distance to [0, 1] based on max_radius
        normalized_r = np.clip(distance / max_radius, 0, 1)
        
        # For Fresnel convex lens: phase = (r^2) / (2*f) * (2*pi / lambda)
        # But we want center thickest, so we use: phase = (1 - r^2/R^2) * NUM_ZONES * 2*pi
        # This creates NUM_ZONES zones where center has max phase, edge has min phase
        # Then apply modulo to create periodic zone structure
        normalized_r_sq = normalized_r ** 2
        phase_factor = 1.0 - normalized_r_sq  # 1 at center, 0 at edge
        phase = phase_factor * num_zones * 2.0 * math.pi
        
        # Apply modulo to create periodic zone structure (Fresnel zones)
        # This creates rings where phase wraps around
        phase_normalized = phase % (2.0 * math.pi)
        
        # Map phase to grayscale [0, 255]
        # For Fresnel convex lens: center thickest (darkest), edge thinnest (lightest)
        # Phase creates periodic zones, but overall trend: center -> edge gets lighter
        
        # First, create periodic zone pattern from phase
        zone_grayscale = np.round(255 - (phase_normalized / (2.0 * math.pi)) * 255).astype(np.uint8)
        
        # Then, add overall gradient: center darker, edge lighter
        # This ensures center is always thicker than edge (convex lens property)
        gradient_factor = 1.0 - normalized_r_sq  # 1 at center, 0 at edge
        # Center should be much darker, so subtract more at center
        gradient_adjustment = gradient_factor * 150  # Adjust by up to 150 gray levels
        grayscale_values = np.clip(zone_grayscale.astype(float) - gradient_adjustment, 0, 255).astype(np.uint8)
        
        if invert_phase:
            grayscale_values = 255 - grayscale_values
    elif zone_type == "blazed":
        # Blazed zones: sawtooth profile within each zone
        normalized_r_sq = np.clip((distance / max_radius) ** 2, 0, 1)
        zone_numbers = (normalized_r_sq * num_zones).astype(int)
        zone_numbers = np.clip(zone_numbers, 0, num_zones - 1)
        
        # Calculate position within zone
        zone_start = zone_numbers.astype(float) / num_zones
        zone_end = (zone_numbers + 1).astype(float) / num_zones
        position_in_zone = (normalized_r_sq - zone_start) / (zone_end - zone_start + 1e-10)
        position_in_zone = np.clip(position_in_zone, 0, 1)
        
        # Sawtooth: linear ramp within each zone
        # Invert: thicker at zone start -> darker
        grayscale_values = np.round(255 - position_in_zone * 255).astype(np.uint8)
        
        if invert_phase:
            grayscale_values = 255 - grayscale_values
    else:
        # Default to continuous (convex lens)
        normalized_r = np.clip(distance / max_radius, 0, 1)
        normalized_r_sq = normalized_r ** 2
        phase_factor = 1.0 - normalized_r_sq  # 1 at center, 0 at edge
        phase = phase_factor * num_zones * 2.0 * math.pi
        phase_normalized = phase % (2.0 * math.pi)
        # Create periodic zone pattern
        zone_grayscale = np.round(255 - (phase_normalized / (2.0 * math.pi)) * 255).astype(np.uint8)
        
        # Add overall gradient: center darker, edge lighter
        gradient_factor = 1.0 - normalized_r_sq
        gradient_adjustment = gradient_factor * 150
        grayscale_values = np.clip(zone_grayscale.astype(float) - gradient_adjustment, 0, 255).astype(np.uint8)
        
        if invert_phase:
            grayscale_values = 255 - grayscale_values
    
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

def verify_image(image, cx, cy, max_radius, num_zones):
    """
    Perform self-check verification of the generated image.
    
    Args:
        image: Generated image array
        cx, cy: Lens center coordinates
        max_radius: Maximum radius
        num_zones: Number of zones
    """
    print("\n=== SELF-CHECK VERIFICATION ===")
    
    # Check center value
    center_value = image[cy, cx]
    print(f"Center value: {center_value}")
    
    # Check values at zone boundaries
    print("Grayscale values at zone boundaries:")
    for zone in range(min(5, num_zones)):
        # Calculate zone boundary radius
        normalized_r_sq = (zone + 1) / num_zones
        r = math.sqrt(normalized_r_sq) * max_radius
        
        x = int(cx + r)
        y = cy
        if 0 <= x < image.shape[1] and 0 <= y < image.shape[0]:
            gray_value = image[y, x]
            print(f"  Zone {zone} boundary (r={r:.1f} px): {gray_value}")
    
    # Check edge value
    edge_x = int(cx + max_radius)
    edge_y = cy
    if 0 <= edge_x < image.shape[1] and 0 <= edge_y < image.shape[0]:
        edge_value = image[edge_y, edge_x]
        print(f"Edge value (at max_radius): {edge_value}")
    
    # Print image statistics
    print(f"Image dtype: {image.dtype}")
    print(f"Image min: {image.min()}")
    print(f"Image max: {image.max()}")
    print(f"Image shape: {image.shape}")
    print(f"Zone type: {ZONE_TYPE}")
    print(f"Number of zones: {num_zones}")

def main():
    """
    Main function to generate and save the greyscale Fresnel lens image.
    """
    print("Generating greyscale Fresnel lens image...")
    print(f"Zone type: {ZONE_TYPE}")
    print(f"Number of zones: {NUM_ZONES}")
    print(f"Focal length: {FOCAL_LENGTH} px")
    print(f"Wavelength: {WAVELENGTH} nm")
    
    # Generate the Fresnel lens image
    image = generate_fresnel_lens_image(
        width=WIDTH,
        height=HEIGHT,
        cx=CX,
        cy=CY,
        max_radius=MAX_RADIUS,
        focal_length=FOCAL_LENGTH,
        wavelength=WAVELENGTH,
        num_zones=NUM_ZONES,
        zone_type=ZONE_TYPE,
        phase_mapping=PHASE_MAPPING,
        invert_phase=INVERT_PHASE,
        background_gray=BACKGROUND_GRAY,
        lens_outside_gray=LENS_OUTSIDE_GRAY
    )
    
    # Save images
    save_image(image, PNG_FILENAME)
    
    # Perform self-check verification
    verify_image(image, CX, CY, MAX_RADIUS, NUM_ZONES)
    
    print("\nGeneration complete!")

if __name__ == "__main__":
    main()
