# -*- coding: utf-8 -*-
"""OpenCV-compatible CV marker generation for layout embedding."""

import klayout.db as db

from utils.geometry import GeometryUtils
from utils.aruco_predefined import ARUCO_PAYLOAD_HEX


class CVMarkUtils:
    FAMILY_LABELS = {
        "aruco4x4": "OpenCV ArUco 4x4",
        "aruco5x5": "OpenCV ArUco 5x5",
        "aruco6x6": "OpenCV ArUco 6x6",
        "aruco_original": "OpenCV ArUco Original",
    }
    DEPTH_ORDER = ("50", "100", "250", "1000")
    FAMILY_ORDER = ("aruco4x4", "aruco5x5", "aruco6x6", "aruco_original")

    @classmethod
    def _encoding_key(cls, family, depth):
        family = str(family or "aruco4x4").lower()
        depth = str(depth or "auto").lower()
        if family == "aruco_original":
            return "aruco_original"
        if family not in ("aruco4x4", "aruco5x5", "aruco6x6"):
            raise ValueError(f"Unknown CV marker family: {family}")
        if depth == "auto":
            depth = cls.DEPTH_ORDER[0]
        if depth not in cls.DEPTH_ORDER:
            raise ValueError(f"Unknown CV marker dictionary depth: {depth}")
        return f"{family}_{depth}"

    @classmethod
    def split_encoding(cls, encoding):
        key = str(encoding or "auto").lower()
        if key == "auto":
            return "aruco4x4", "auto"
        if key == "aruco_original":
            return "aruco_original", "auto"
        for family in ("aruco4x4", "aruco5x5", "aruco6x6"):
            prefix = f"{family}_"
            if key.startswith(prefix):
                return family, key[len(prefix) :]
        raise ValueError(f"Unknown CV marker encoding: {encoding}")

    @classmethod
    def encoding_spec(cls, encoding):
        key = str(encoding or "auto").lower()
        if key == "auto":
            key = cls._encoding_key("aruco4x4", "50")
        if key not in ARUCO_PAYLOAD_HEX:
            raise ValueError(f"Unknown CV marker encoding: {encoding}")
        side, capacity, hex_width, opencv_name, _payload_hex = ARUCO_PAYLOAD_HEX[key]
        family, depth = cls.split_encoding(key)
        label = cls.FAMILY_LABELS[family] if family == "aruco_original" else f"{cls.FAMILY_LABELS[family]} {depth}"
        return {
            "key": key,
            "family": family,
            "depth": depth,
            "label": label,
            "marker_size": side,
            "capacity": capacity,
            "hex_width": hex_width,
            "opencv_name": opencv_name,
        }

    @classmethod
    def resolve_encoding(cls, encoding=None, required_count=1, family=None, depth=None):
        required_count = max(int(required_count), 1)
        if family is None and depth is None:
            family, depth = cls.split_encoding(encoding)
        else:
            family = str(family or "aruco4x4").lower()
            depth = str(depth or "auto").lower()

        if family == "aruco_original":
            if cls.capacity("aruco_original") >= required_count:
                return "aruco_original"
            raise ValueError(f"DICT_ARUCO_ORIGINAL cannot contain {required_count} IDs.")

        if depth != "auto":
            key = cls._encoding_key(family, depth)
            cls.encoding_spec(key)
            return key

        for candidate_depth in cls.DEPTH_ORDER:
            candidate = cls._encoding_key(family, candidate_depth)
            if cls.capacity(candidate) >= required_count:
                return candidate
        raise ValueError(f"No CV marker encoding can contain {required_count} IDs.")

    @classmethod
    def capacity(cls, encoding):
        return int(cls.encoding_spec(encoding)["capacity"])

    @classmethod
    def label(cls, encoding):
        spec = cls.encoding_spec(encoding)
        return f"{spec['label']} ({cls.capacity(encoding)} IDs)"

    @classmethod
    def marker_matrix(cls, marker_id, encoding="aruco4x4_50", border_bits=1):
        spec = cls.encoding_spec(encoding)
        payload_side, capacity, hex_width, _opencv_name, payload_hex = ARUCO_PAYLOAD_HEX[spec["key"]]
        marker_id = int(marker_id)
        if marker_id < 0 or marker_id >= capacity:
            raise ValueError(
                f"{cls.label(encoding)} supports marker IDs 0 to {capacity - 1}, "
                f"but got {marker_id}."
            )

        border_bits = max(int(border_bits), 1)
        total_side = payload_side + 2 * border_bits
        matrix = [[False for _ in range(total_side)] for _ in range(total_side)]

        for row in range(total_side):
            for col in range(total_side):
                if row < border_bits or col < border_bits or row >= total_side - border_bits or col >= total_side - border_bits:
                    matrix[row][col] = True

        start = marker_id * hex_width
        payload_value = int(payload_hex[start : start + hex_width], 16)
        for payload_row in range(payload_side):
            for payload_col in range(payload_side):
                bit_index = payload_side * payload_side - 1 - (payload_row * payload_side + payload_col)
                value = bool((payload_value >> bit_index) & 1)
                matrix[payload_row + border_bits][payload_col + border_bits] = value
        return matrix

    @staticmethod
    def matrix_to_polygons(matrix, x, y, size_um, anchor="left_top", merge=True):
        rows = len(matrix)
        cols = len(matrix[0]) if rows else 0
        if rows <= 0 or cols <= 0:
            return []

        size_um = float(size_um)
        module_size = size_um / float(cols)
        anchor = str(anchor or "left_top").lower()
        if anchor == "left_bottom":
            x0 = float(x)
            top_y = float(y) + size_um
        elif anchor == "right_bottom":
            x0 = float(x) - size_um
            top_y = float(y) + size_um
        elif anchor == "right_top":
            x0 = float(x) - size_um
            top_y = float(y)
        elif anchor == "center":
            x0 = float(x) - size_um / 2.0
            top_y = float(y) + size_um / 2.0
        else:
            x0 = float(x)
            top_y = float(y)

        def rect_shape(col_start, col_end, row_start, row_end):
            width = (col_end - col_start) * module_size
            height = (row_end - row_start) * module_size
            cx = x0 + (col_start + col_end) * module_size / 2.0
            cy = top_y - (row_start + row_end) * module_size / 2.0
            return GeometryUtils.create_rectangle(cx, cy, width, height, center=True)

        shapes = []
        for row_index, row in enumerate(matrix):
            for col_index, is_dark in enumerate(row):
                if not bool(is_dark):
                    continue
                shapes.append(rect_shape(col_index, col_index + 1, row_index, row_index + 1))

        if merge and shapes:
            region = db.Region()
            for shape in shapes:
                region.insert(shape)
            region = region.merged()
            return [polygon for polygon in region.each()]
        return shapes
