# -*- coding: utf-8 -*-

import os
import sys

import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import DEFAULT_UNIT_SCALE
from components.markarray import MarkArrayBuilder, build_cv_mark_array_layout
from utils.cv_mark_utils import CVMarkUtils


def _bbox_um(shape):
    bbox = shape.bbox()
    return (
        bbox.left / DEFAULT_UNIT_SCALE,
        bbox.bottom / DEFAULT_UNIT_SCALE,
        bbox.right / DEFAULT_UNIT_SCALE,
        bbox.top / DEFAULT_UNIT_SCALE,
    )


def test_cv_mark_array_builds_layout():
    layout, cell = build_cv_mark_array_layout(
        sample_width=2500.0,
        sample_height=2500.0,
        active_width=1500.0,
        active_height=1512.0,
        mark_pitch_x=500.0,
        mark_pitch_y=504.0,
        name="cv_mark_array_test",
    )

    assert cell.name == "cv_mark_array_test"
    assert layout.find_layer(1, 0) >= 0
    assert layout.find_layer(2, 0) >= 0
    mark_layer = layout.find_layer(3, 0)
    assert mark_layer >= 0
    assert cell.shapes(mark_layer).size() > 9


def test_cv_marker_id_modes():
    builder = MarkArrayBuilder()

    assert builder._cv_marker_id(0, "aruco4x4_50", "strict") == 0
    assert builder._cv_marker_id(49, "aruco4x4_50", "strict") == 49
    assert builder._cv_marker_id(50, "aruco4x4_50", "modulo") == 0

    with pytest.raises(ValueError, match="OpenCV ArUco 4x4 50"):
        builder._cv_marker_id(50, "aruco4x4_50", "strict")


def test_auto_selects_smallest_encoding():
    assert CVMarkUtils.resolve_encoding(required_count=1, family="aruco4x4", depth="auto") == "aruco4x4_50"
    assert CVMarkUtils.resolve_encoding(required_count=50, family="aruco4x4", depth="auto") == "aruco4x4_50"
    assert CVMarkUtils.resolve_encoding(required_count=51, family="aruco4x4", depth="auto") == "aruco4x4_100"
    assert CVMarkUtils.resolve_encoding(required_count=101, family="aruco5x5", depth="auto") == "aruco5x5_250"
    assert CVMarkUtils.resolve_encoding(required_count=251, family="aruco6x6", depth="auto") == "aruco6x6_1000"
    assert CVMarkUtils.resolve_encoding(required_count=1024, family="aruco_original", depth="auto") == "aruco_original"


def test_strict_mode_rejects_arrays_over_forced_encoding_range():
    with pytest.raises(ValueError, match="OpenCV ArUco 4x4 50"):
        build_cv_mark_array_layout(
            active_width=51.0,
            active_height=1.0,
            mark_pitch_x=1.0,
            mark_pitch_y=1.0,
            cv_encoding="aruco4x4_50",
            aruco_id_mode="strict",
        )


def test_matrix_anchor_geometry():
    left_bottom = CVMarkUtils.matrix_to_polygons([[True]], 10.0, 20.0, 5.0, anchor="left_bottom")[0]
    assert _bbox_um(left_bottom) == pytest.approx((10.0, 20.0, 15.0, 25.0))

    right_bottom = CVMarkUtils.matrix_to_polygons([[True]], 10.0, 20.0, 5.0, anchor="right_bottom")[0]
    assert _bbox_um(right_bottom) == pytest.approx((5.0, 20.0, 10.0, 25.0))

    right_top = CVMarkUtils.matrix_to_polygons([[True]], 10.0, 20.0, 5.0, anchor="right_top")[0]
    assert _bbox_um(right_top) == pytest.approx((5.0, 15.0, 10.0, 20.0))

    left_top = CVMarkUtils.matrix_to_polygons([[True]], 10.0, 20.0, 5.0, anchor="left_top")[0]
    assert _bbox_um(left_top) == pytest.approx((10.0, 15.0, 15.0, 20.0))


def test_cv_quadrant_gap_uses_center_corner_handle():
    builder = MarkArrayBuilder()
    shapes = builder._cv_marker_shapes(0, "aruco4x4_50", 0.0, 0.0, 30.0, anchor="left_bottom", border_bits=1)
    left = min(_bbox_um(shape)[0] for shape in shapes)
    bottom = min(_bbox_um(shape)[1] for shape in shapes)

    assert left == pytest.approx(0.0)
    assert bottom == pytest.approx(0.0)


def test_cv_bonecross_uses_parametric_split_style():
    builder = MarkArrayBuilder()
    shapes = builder._cv_main_mark_shapes(
        0.0,
        0.0,
        "bonecross",
        mark_size=80.0,
        mark_width=10.0,
        mark_fine_width=6.0,
        mark_fine_ratio=0.2,
    )

    assert len(shapes) == 1


def test_cv_marker_polygons_are_merged():
    matrix = [
        [True, True, False],
        [True, True, False],
        [False, True, True],
    ]
    merged = CVMarkUtils.matrix_to_polygons(matrix, 0.0, 0.0, 30.0, merge=True)
    unmerged = CVMarkUtils.matrix_to_polygons(matrix, 0.0, 0.0, 30.0, merge=False)

    assert len(unmerged) == 6
    assert len(merged) == 1


def test_cv_marker_matches_opencv_aruco_if_available():
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    if not hasattr(cv2, "aruco"):
        pytest.skip("OpenCV aruco module is unavailable")

    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
    marker_id = 42
    matrix = np.array(CVMarkUtils.marker_matrix(marker_id, "aruco4x4_250", border_bits=1), dtype=bool)
    image = (~matrix).astype(np.uint8) * 255
    expected = cv2.aruco.generateImageMarker(dictionary, marker_id, 6, borderBits=1)

    assert np.array_equal(image, expected)

    canvas = np.full((220, 220), 255, dtype=np.uint8)
    marker = np.kron(image, np.ones((24, 24), dtype=np.uint8))
    canvas[38 : 38 + marker.shape[0], 38 : 38 + marker.shape[1]] = marker
    if hasattr(cv2.aruco, "ArucoDetector"):
        detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
        _corners, ids, _rejected = detector.detectMarkers(canvas)
    else:
        _corners, ids, _rejected = cv2.aruco.detectMarkers(canvas, dictionary)

    assert ids is not None
    assert marker_id in ids.flatten().tolist()


def test_supported_marker_families_match_opencv_if_available():
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    if not hasattr(cv2, "aruco"):
        pytest.skip("OpenCV aruco module is unavailable")

    samples = [
        ("aruco4x4_250", cv2.aruco.DICT_4X4_250, 42),
        ("aruco5x5_250", cv2.aruco.DICT_5X5_250, 42),
        ("aruco6x6_250", cv2.aruco.DICT_6X6_250, 42),
        ("aruco_original", cv2.aruco.DICT_ARUCO_ORIGINAL, 42),
    ]
    for encoding, cv_dict, marker_id in samples:
        dictionary = cv2.aruco.getPredefinedDictionary(cv_dict)
        side = dictionary.markerSize + 2
        matrix = np.array(CVMarkUtils.marker_matrix(marker_id, encoding, border_bits=1), dtype=bool)
        image = (~matrix).astype(np.uint8) * 255
        expected = cv2.aruco.generateImageMarker(dictionary, marker_id, side, borderBits=1)

        assert np.array_equal(image, expected)
