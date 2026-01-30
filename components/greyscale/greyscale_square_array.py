#!/usr/bin/env python3
"""
Greyscale Square Array Generator
Creates single-channel 8-bit images with square array pattern for grayscale lithography.
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

# Square array parameters
SQUARE_SIZE = 50  # Size of each square
SPACING = 0  # Spacing between squares (0 for tessellation, >0 for grid)
ARRAY_ROWS = 16  # Number of rows
ARRAY_COLS = 16  # Number of columns

# Background and square parameters
BACKGROUND_GRAY = 0

# Gradient pattern parameters
GRADIENT_PATTERN = "snake_fold"  # Options: "snake_spiral", "snake_fold", "random", "uniform"
UNIFORM_GRAY = 255  # Color for uniform pattern
RANDOM_SEED = 42  # Seed for random pattern

# Border parameters
BORDER_WIDTH = 10  # Unified border width for squares and colorbar
BORDER_GRAY = 255

# Corner mark parameters
CORNER_MARK_SIZE = 50  # Size of L-shaped corner marks
CORNER_MARK_THICKNESS = 10  # Thickness of corner mark lines
CORNER_MARK_GRAY = 255  # Color of corner marks
CORNER_MARK_OFFSET = 0  # No offset - marks at exact corners

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

TIFF_FILENAME = get_image_path("greyscale_square_array_1024.tif")
BMP_FILENAME = get_image_path("greyscale_square_array_1024.bmp")

# =============================================================================
# FUNCTIONS
# =============================================================================

def calculate_gradient_values(rows, cols, pattern, random_seed=42):
    """
    Calculate gradient values for each square in the array.
    
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

def generate_square_array_image(width, height, square_size, spacing, rows, cols, background_gray=0, pattern="uniform"):
    """
    Generate a single-channel 8-bit image with square array pattern.
    
    Args:
        width, height: Canvas dimensions
        square_size: Size of each square
        spacing: Spacing between squares
        rows, cols: Number of rows and columns
        background_gray: Background pixel value
        pattern: Gradient pattern type
        
    Returns:
        np.ndarray: Single-channel uint8 image array
    """
    # Initialize image with background
    image = np.full((height, width), background_gray, dtype=np.uint8)
    
    # Calculate gradient values for each square
    gradient_values = calculate_gradient_values(rows, cols, pattern, RANDOM_SEED)
    
    # Calculate array center position
    total_array_width = cols * square_size + (cols - 1) * spacing
    total_array_height = rows * square_size + (rows - 1) * spacing
    start_x = (width - total_array_width) // 2
    start_y = (height - total_array_height) // 2 - 80  # Move up to balance with colorbar
    
    # Draw squares with gradient values
    for row in range(rows):
        for col in range(cols):
            # Calculate square position
            x = start_x + col * (square_size + spacing)
            y = start_y + row * (square_size + spacing)
            
            # Get gradient value for this square
            gray_value = gradient_values[row, col]
            
            # Draw square with gradient value
            for i in range(square_size):
                for j in range(square_size):
                    px = x + i
                    py = y + j
                    if 0 <= px < width and 0 <= py < height:
                        image[py, px] = gray_value
    
    return image

def draw_square_borders(image, width, height, square_size, spacing, rows, cols, border_width, border_gray):
    """
    Draw borders around all squares.
    
    Args:
        image: Image array to modify in-place
        width, height: Canvas dimensions
        square_size: Size of each square
        spacing: Spacing between squares
        rows, cols: Number of rows and columns
        border_width: Width of the borders
        border_gray: Pixel value for borders
    """
    # Calculate array center position
    total_array_width = cols * square_size + (cols - 1) * spacing
    total_array_height = rows * square_size + (rows - 1) * spacing
    start_x = (width - total_array_width) // 2
    start_y = (height - total_array_height) // 2 - 80  # Move up to balance with colorbar
    
    # Draw borders around each square
    for row in range(rows):
        for col in range(cols):
            # Calculate square position
            x = start_x + col * (square_size + spacing)
            y = start_y + row * (square_size + spacing)
            
            # Draw border around square
            for bw in range(border_width):
                # Top border
                for i in range(square_size + 2 * bw):
                    px = x - bw + i
                    py = y - bw
                    if 0 <= px < width and 0 <= py < height:
                        image[py, px] = border_gray
                
                # Bottom border
                for i in range(square_size + 2 * bw):
                    px = x - bw + i
                    py = y + square_size + bw - 1
                    if 0 <= px < width and 0 <= py < height:
                        image[py, px] = border_gray
                
                # Left border
                for j in range(square_size + 2 * bw):
                    px = x - bw
                    py = y - bw + j
                    if 0 <= px < width and 0 <= py < height:
                        image[py, px] = border_gray
                
                # Right border
                for j in range(square_size + 2 * bw):
                    px = x + square_size + bw - 1
                    py = y - bw + j
                    if 0 <= px < width and 0 <= py < height:
                        image[py, px] = border_gray

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

def draw_colorbar(image, x, y, width, height):
    """
    Draw a horizontal colorbar showing grayscale relationship.
    
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

def verify_image(image):
    """
    Perform self-check verification of the generated image.
    
    Args:
        image: Generated image array
    """
    print("\n=== SELF-CHECK VERIFICATION ===")
    
    # Print image statistics
    print(f"Image dtype: {image.dtype}")
    print(f"Image min: {image.min()}")
    print(f"Image max: {image.max()}")
    print(f"Image shape: {image.shape}")
    
    # Check corner marks
    print("Corner mark verification:")
    corners = [(0, 0), (image.shape[1]-1, 0), (0, image.shape[0]-1), (image.shape[1]-1, image.shape[0]-1)]
    for i, (x, y) in enumerate(corners):
        corner_value = image[y, x]
        print(f"  Corner {i+1}: {corner_value}")

def main():
    """
    Main function to generate and save the greyscale square array image.
    """
    print("Generating greyscale square array image...")
    
    # Generate the square array image
    image = generate_square_array_image(
        width=WIDTH,
        height=HEIGHT,
        square_size=SQUARE_SIZE,
        spacing=SPACING,
        rows=ARRAY_ROWS,
        cols=ARRAY_COLS,
        background_gray=BACKGROUND_GRAY,
        pattern=GRADIENT_PATTERN
    )
    
    # No borders for square tessellation - squares should be seamless
    
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
    
    # Draw colorbar
    draw_colorbar(
        image=image,
        x=COLORBAR_X,
        y=COLORBAR_Y,
        width=COLORBAR_WIDTH,
        height=COLORBAR_HEIGHT
    )
    
    # Save images
    save_image(image, TIFF_FILENAME, BMP_FILENAME, OUTPUT_FORMAT, OUTPUT_BOTH)
    
    # Perform self-check verification
    verify_image(image)
    
    print("\nGeneration complete!")

if __name__ == "__main__":
    main()
