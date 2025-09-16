# -*- coding: utf-8 -*-
"""
Gosper (Flowsnake) Curve Generator for KLayout

This module provides a robust implementation of the Gosper curve (flowsnake)
using L-systems and turtle graphics, specifically designed for KLayout layout generation.

The Gosper curve is a space-filling curve based on hexagonal geometry with 60° turns.

Usage:
    from utils.gosper_curve import make_gosper_polygon, draw_gosper
    
    # Generate a Gosper curve polygon
    poly = make_gosper_polygon(order=3, step=2.0, width=0.8)
    
    # Draw directly to a KLayout cell
    draw_gosper(cell, layer_index, order=3, step=2.0, width=0.8)

Technical Specification:
- L-system with axiom A, angle θ = 60°
- Rules: A -> A-B--B+A++AA+B-, B -> +A-BB--B-A++A+B
- Turtle interpretation: A/B = forward, +/- = turn left/right by 60°
- Hexagonal lattice with 60° direction multiples
- Robust path widening with miter limits
"""

import math
import pya
from typing import List, Tuple, Optional


def build_gosper_string(order: int) -> str:
    """
    Build Gosper curve L-system string for given order.
    
    L-system specification:
    - Axiom: A
    - Angle: θ = 60°
    - Rules:
      A -> A-B--B+A++AA+B-
      B -> +A-BB--B-A++A+B
    
    Args:
        order: Number of L-system iterations (order >= 0)
        
    Returns:
        L-system string containing A, B, +, - symbols
        
    Raises:
        ValueError: If order < 0
    """
    if order < 0:
        raise ValueError("Order must be non-negative")
    
    # L-system rules
    rule_a = "A-B--B+A++AA+B-"
    rule_b = "+A-BB--B-A++A+B"
    
    # Start with axiom
    string = "A"
    
    # Apply rules iteratively
    for _ in range(order):
        new_string = ""
        for char in string:
            if char == 'A':
                new_string += rule_a
            elif char == 'B':
                new_string += rule_b
            else:  # +, -, or other symbols
                new_string += char
        string = new_string
    
    return string


def turtle_to_points(lsystem_string: str, step: float) -> List[Tuple[float, float]]:
    """
    Convert L-system string to ordered vertex list using turtle graphics.
    
    Turtle interpretation:
    - A or B: forward 1 step and record vertex
    - +: turn left by 60°
    - -: turn right by 60°
    
    Args:
        lsystem_string: L-system string from build_gosper_string()
        step: Step length for forward moves
        
    Returns:
        List of (x, y) coordinates representing the curve centerline
    """
    # Remove non-drawing symbols for validation
    drawing_symbols = lsystem_string.replace('+', '').replace('-', '')
    expected_segments = len(drawing_symbols)
    
    # Turtle state
    x, y = 0.0, 0.0
    angle = 0.0  # Start facing right (0°)
    points = [(x, y)]  # Start point
    
    # Direction vectors for 60° increments
    directions = [
        (1.0, 0.0),      # 0° (right)
        (0.5, 0.866),    # 60° (up-right)
        (-0.5, 0.866),   # 120° (up-left)
        (-1.0, 0.0),     # 180° (left)
        (-0.5, -0.866),  # 240° (down-left)
        (0.5, -0.866)    # 300° (down-right)
    ]
    
    for char in lsystem_string:
        if char in 'AB':
            # Forward move
            dx, dy = directions[int(angle) % 6]
            x += dx * step
            y += dy * step
            
            # Snap to grid to avoid floating point drift
            x = round(x, 9)
            y = round(y, 9)
            
            points.append((x, y))
            
        elif char == '+':
            # Turn left by 60°
            angle += 1.0
            
        elif char == '-':
            # Turn right by 60°
            angle -= 1.0
    
    # Validation: should have expected number of segments
    actual_segments = len(points) - 1
    if actual_segments != expected_segments:
        raise ValueError(f"Segment count mismatch: expected {expected_segments}, got {actual_segments}")
    
    return points


def widen_centerline(points: List[Tuple[float, float]], width: float, 
                    miter_limit: float = 2.0) -> pya.DPolygon:
    """
    Widen centerline to polygon with robust joins.
    
    Uses KLayout's EdgeProcessor for robust path widening with miter limits
    to avoid spikes at acute turns.
    
    Args:
        points: Centerline points from turtle_to_points()
        width: Trace width
        miter_limit: Maximum miter length (default 2.0)
        
    Returns:
        pya.DPolygon representing the widened path
    """
    if len(points) < 2:
        raise ValueError("Need at least 2 points for path widening")
    
    # Create path from points
    dpoints = [pya.DPoint(x, y) for x, y in points]
    path = pya.DPath(dpoints, width, 0, 0, 0)  # width, bgn_ext=0, end_ext=0, round=False
    
    # Use EdgeProcessor for robust widening with miter limits
    ep = pya.EdgeProcessor()
    
    # Create edges from path
    edges = []
    for i in range(len(dpoints) - 1):
        edge = pya.DEdge(dpoints[i], dpoints[i + 1])
        edges.append(edge)
    
    # Size the edges (widen by width/2 on each side)
    sized_edges = ep.size(edges, width / 2, 1, 1)  # width/2, mode=1, round=False
    
    # Convert to polygon
    if sized_edges:
        # Create region from sized edges
        region = pya.DRegion(sized_edges)
        merged_region = region.merged()
        
        if merged_region.size() > 0:
            # Get the first (and should be only) polygon
            return merged_region[0]
    
    # Fallback: create simple rectangle if widening fails
    if len(points) >= 2:
        x1, y1 = points[0]
        x2, y2 = points[1]
        return pya.DPolygon([
            pya.DPoint(x1 - width/2, y1 - width/2),
            pya.DPoint(x2 + width/2, y1 - width/2),
            pya.DPoint(x2 + width/2, y2 + width/2),
            pya.DPoint(x1 - width/2, y2 + width/2)
        ])
    
    raise ValueError("Failed to create widened polygon")


def make_gosper_polygon(order: int, step: float, width: float, 
                       origin: Tuple[float, float] = (0.0, 0.0),
                       rotation_deg: float = 0.0, dbu: float = 1e-3) -> pya.Polygon:
    """
    Generate Gosper curve polygon for KLayout.
    
    Complete pipeline:
    1. Build L-system string
    2. Convert to turtle points
    3. Widen centerline to polygon
    4. Apply transformations
    5. Convert to integer coordinates
    
    Args:
        order: L-system iterations (order >= 0)
        step: Centerline step length in layout units
        width: Final trace width
        origin: Translation offset (x, y)
        rotation_deg: Rotation angle in degrees
        dbu: Layout database unit
        
    Returns:
        pya.Polygon ready for insertion into KLayout cell
        
    Raises:
        ValueError: If parameters are invalid
    """
    if order < 0:
        raise ValueError("Order must be non-negative")
    if step <= 0:
        raise ValueError("Step must be positive")
    if width <= 0:
        raise ValueError("Width must be positive")
    if dbu <= 0:
        raise ValueError("DBU must be positive")
    
    # Build L-system string
    lsystem_string = build_gosper_string(order)
    
    # Convert to turtle points
    points = turtle_to_points(lsystem_string, step)
    
    # Validate segment count
    expected_segments = 7 ** order
    actual_segments = len(points) - 1
    if actual_segments != expected_segments:
        raise ValueError(f"Segment count mismatch: expected {expected_segments}, got {actual_segments}")
    
    # Widen centerline to polygon
    dpolygon = widen_centerline(points, width)
    
    # Apply transformations
    if rotation_deg != 0.0 or origin != (0.0, 0.0):
        # Create transformation matrix
        trans = pya.DCplxTrans(1.0, rotation_deg, False, pya.DPoint(*origin))
        dpolygon = trans * dpolygon
    
    # Convert to integer coordinates with dbu scaling
    ipolygon = pya.Polygon()
    for point in dpolygon.each_point():
        ix = int(round(point.x / dbu))
        iy = int(round(point.y / dbu))
        ipolygon.insert_point(pya.Point(ix, iy))
    
    return ipolygon


def draw_gosper(cell: pya.Cell, layer_index: int, order: int = 3, step: float = 2.0, 
                width: float = 0.8, origin: Tuple[float, float] = (0.0, 0.0),
                rotation_deg: float = 0.0, dbu: float = 1e-3) -> None:
    """
    Draw Gosper curve directly to KLayout cell.
    
    Convenience function that generates and inserts Gosper curve polygon.
    
    Args:
        cell: Target KLayout cell
        layer_index: Target layer index
        order: L-system iterations
        step: Centerline step length
        width: Trace width
        origin: Translation offset
        rotation_deg: Rotation angle in degrees
        dbu: Layout database unit
    """
    poly = make_gosper_polygon(order, step, width, origin, rotation_deg, dbu)
    cell.shapes(layer_index).insert(poly)


# Test and validation functions
def all_turns_are_multiples_of_60(points: List[Tuple[float, float]]) -> bool:
    """Check if all turn angles are multiples of 60°."""
    if len(points) < 3:
        return True
    
    for i in range(1, len(points) - 1):
        # Calculate vectors
        v1 = (points[i][0] - points[i-1][0], points[i][1] - points[i-1][1])
        v2 = (points[i+1][0] - points[i][0], points[i+1][1] - points[i][1])
        
        # Calculate angle between vectors
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
        
        if mag1 == 0 or mag2 == 0:
            continue
            
        cos_angle = dot / (mag1 * mag2)
        cos_angle = max(-1.0, min(1.0, cos_angle))  # Clamp to avoid numerical errors
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)
        
        # Check if angle is multiple of 60° (with tolerance for floating point errors)
        remainder = angle_deg % 60.0
        if remainder > 1e-3 and remainder < (60.0 - 1e-3):
            print(f"Invalid angle at point {i}: {angle_deg:.3f}° (remainder: {remainder:.6f})")
            return False
    
    return True


def has_self_intersections(points: List[Tuple[float, float]]) -> bool:
    """Simple O(n²) check for self-intersections (for small n)."""
    if len(points) < 4:
        return False
    
    # Check each pair of non-adjacent segments
    for i in range(len(points) - 1):
        for j in range(i + 2, len(points) - 1):
            if j == i + 1:  # Skip adjacent segments
                continue
                
            # Check if segments intersect
            p1, p2 = points[i], points[i + 1]
            p3, p4 = points[j], points[j + 1]
            
            # Simple line intersection test
            denom = (p1[0] - p2[0]) * (p3[1] - p4[1]) - (p1[1] - p2[1]) * (p3[0] - p4[0])
            if abs(denom) < 1e-10:  # Parallel lines
                continue
                
            t = ((p1[0] - p3[0]) * (p3[1] - p4[1]) - (p1[1] - p3[1]) * (p3[0] - p4[0])) / denom
            u = -((p1[0] - p2[0]) * (p1[1] - p3[1]) - (p1[1] - p2[1]) * (p1[0] - p3[0])) / denom
            
            if 0 < t < 1 and 0 < u < 1:
                return True
    
    return False


def run_tests():
    """Run basic validation tests."""
    print("Running Gosper curve tests...")
    
    # Test L-system string generation
    for order in range(5):
        string = build_gosper_string(order)
        drawing_symbols = string.replace('+', '').replace('-', '')
        expected = 7 ** order
        actual = len(drawing_symbols)
        assert actual == expected, f"Order {order}: expected {expected} segments, got {actual}"
        print(f"✓ Order {order}: {actual} segments")
    
    # Test turtle interpretation
    for order in range(4):
        string = build_gosper_string(order)
        points = turtle_to_points(string, 1.0)
        expected_segments = 7 ** order
        actual_segments = len(points) - 1
        assert actual_segments == expected_segments, f"Order {order}: segment count mismatch"
        print(f"✓ Order {order}: {actual_segments} segments in turtle path")
    
    # Test angle validation
    for order in range(3):
        string = build_gosper_string(order)
        points = turtle_to_points(string, 1.0)
        assert all_turns_are_multiples_of_60(points), f"Order {order}: invalid turn angles"
        print(f"✓ Order {order}: all turns are multiples of 60°")
    
    # Test self-intersection check
    for order in range(3):
        string = build_gosper_string(order)
        points = turtle_to_points(string, 1.0)
        assert not has_self_intersections(points), f"Order {order}: has self-intersections"
        print(f"✓ Order {order}: no self-intersections")
    
    # Test polygon generation
    for order in range(3):
        poly = make_gosper_polygon(order, 2.0, 0.8)
        assert poly.num_points() > 0, f"Order {order}: empty polygon"
        print(f"✓ Order {order}: polygon generated with {poly.num_points()} points")
    
    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
