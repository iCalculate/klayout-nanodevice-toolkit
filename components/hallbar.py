# -*- coding: utf-8 -*-
"""
Hall Bar器件模块 - 定义完整的霍尔bar器件结构
Hall Bar device module - defines the complete Hall bar device structure.
"""

import sys
import os
import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import klayout.db as db
try:
    import pya
except ImportError:
    pya = db

from config import LAYER_DEFINITIONS, PROCESS_CONFIG
from utils.geometry import GeometryUtils
from utils.mark_utils import MarkUtils
from utils.fanout_utils import draw_pad, draw_trapezoidal_fanout
from utils.text_utils import TextUtils
from typing import cast, Literal

class HallBar:
    """Hall Bar器件类
    Hall Bar device class.
    """
    def __init__(self, layout=None, **kwargs):
        self.layout = layout or db.Layout()
        dist_v_value = kwargs.get('dist_v', kwargs.get('Dist_V', 25.0))
        label_anchor_value = kwargs.get('label_anchor', kwargs.get('label_cursor', 'left_top'))
        source_drain_layer_id = int(kwargs.get('source_drain_layer_id', 15))
        default_fine_layer_id = (
            source_drain_layer_id + 10
            if 11 <= source_drain_layer_id <= 19
            else LAYER_DEFINITIONS['fine_source_drain']['id']
        )
        self._layer_ids = {
            'channel': kwargs.get('channel_layer_id', 13),
            'source_drain': source_drain_layer_id,
            'fine_source_drain': int(kwargs.get('fine_source_drain_layer_id', default_fine_layer_id)),
            'labels': kwargs.get('label_layer_id', 3),
            'alignment_marks': kwargs.get('alignment_mark_layer_id', 3),
            'parameter_labels': kwargs.get('parameter_label_layer_id', 6),
        }
        self.setup_layers()

        # ===== 沟道与突出参数 =====
        self.bar_length = kwargs.get('bar_length', 50.0)      # 沟道长度 (μm)
        self.bar_width = kwargs.get('bar_width', 10.0)        # 沟道主宽度 (μm)
        self.v_protrude = kwargs.get('v_protrude_width', 3.0)       # V区突出宽度 (μm)
        self.v_protrude_length = kwargs.get('v_protrude_length', 5.0)  # V区突出区域长度(沿沟道方向)
        self.dist_v = dist_v_value                            # V电极间距 (μm)
        self.v_contact_pairs = int(kwargs.get('v_contact_pairs', kwargs.get('v_pair_count', 2)))
        self.min_electrode_gap = float(kwargs.get('min_electrode_gap', 2.0))
        self.outer_pad_gap = float(kwargs.get('outer_pad_gap', 10.0))
        self.min_fanout_corner_angle = float(kwargs.get('min_fanout_corner_angle', 20.0))
        # 0 means use the complete usable edge of the large pad.
        self.coarse_fanout_pad_edge_width = float(kwargs.get('coarse_fanout_pad_edge_width', 0.0))

        # ===== V电极参数 =====
        self.v_inner_length = kwargs.get('v_inner_length', None)  # 沿沟道方向，None时自动联动
        self.v_inner_width = kwargs.get('v_inner_width', 2.0)    # 沟道宽度方向
        self.v_outer_length = kwargs.get('v_outer_length', 100.0)
        self.v_outer_width = kwargs.get('v_outer_width', 100.0)
        self.v_outer_offset = kwargs.get('v_outer_offset', 18.0) 
        self.v_outer_chamfer = kwargs.get('v_outer_chamfer', 10.0)
        self.v_outer_chamfer_type = kwargs.get('v_outer_chamfer_type', 'straight')
        self.v_fanout_type = kwargs.get('v_fanout_type', 'trapezoidal')
        self.v_outer_offset_x = kwargs.get('v_outer_offset_x', 60)
        self.v_outer_offset_y = kwargs.get('v_outer_offset_y', 120)

        # ===== I电极参数 =====
        self.i_inner_length = kwargs.get('i_inner_length', 10.0)
        self.i_inner_width = kwargs.get('i_inner_width', None)  # None时自动联动
        self.i_outer_length = kwargs.get('i_outer_length', 100.0)
        self.i_outer_width = kwargs.get('i_outer_width', 100.0)
        self.i_outer_offset = kwargs.get('i_outer_offset', 25.0)
        self.i_outer_chamfer = kwargs.get('i_outer_chamfer', 10.0)
        self.i_outer_chamfer_type = kwargs.get('i_outer_chamfer_type', 'straight')
        self.i_fanout_type = kwargs.get('i_fanout_type', 'trapezoidal')
        self.i_outer_offset_x = kwargs.get('i_outer_offset_x', 150)
        self.i_outer_offset_y = kwargs.get('i_outer_offset_y', 0.0)

        # EBL split: channel-side contacts and short leads use the matching
        # 21-29 layer; bridge pads, probe pads and coarse fanout stay on 11-19.
        self.split_ebl_exposure = bool(kwargs.get('split_ebl_exposure', False))
        self.fine_fanout_length = float(kwargs.get('fine_fanout_length', 12.0))
        self.bridge_pad_length = float(kwargs.get('bridge_pad_length', 12.0))
        self.bridge_pad_width = float(kwargs.get('bridge_pad_width', 10.0))
        self.ebl_overlap = float(kwargs.get('ebl_overlap', 2.0))

        # 自动调整outer_offset，保证pad间距不小于10um
        min_pad_gap = 10.0
        min_gap = 20.0
        # I电极outer pad中心x方向偏移
        self.i_outer_offset = kwargs.get('i_outer_offset', self.bar_length/2 + self.i_outer_length/2 + min_gap)
        # V电极outer pad中心y方向偏移
        self.v_outer_offset = kwargs.get('v_outer_offset', (self.bar_width + self.v_protrude)/2 + self.v_outer_length/2 + min_gap)

        # ===== 其余参数 =====
        self.device_margin_x = kwargs.get('device_margin_x', 250.0)
        self.device_margin_y = kwargs.get('device_margin_y', 200.0)
        self.mark_size = kwargs.get('mark_size', 15.0)
        self.mark_width = kwargs.get('mark_width', 2.0)
        self.mark_types = kwargs.get('mark_types', ['sq_missing', 'l', 'l', 'cross'])
        self.mark_rotations = kwargs.get('mark_rotations', [0, 0, 2, 1])
        self.label_size = kwargs.get('label_size', 20.0)
        self.label_font = kwargs.get('label_font', 'C:/Windows/Fonts/OCRAEXT.TTF')
        self.label_anchor = label_anchor_value  # 编号位置: 'right_bottom', 'right_top', 'left_bottom', 'left_top'
        self.label_offset_x = kwargs.get('label_offset_x',  10.0)
        self.label_offset_y = kwargs.get('label_offset_y', -10.0)
        self.electrode_text_label = kwargs.get('electrode_text_label', False)  # 是否为电极添加KLayout text label
        self._validate()

    def setup_layers(self):
        for layer_name, layer_info in LAYER_DEFINITIONS.items():
            self.layout.layer(layer_info['id'], 0)
        for layer_id in self._layer_ids.values():
            self.layout.layer(layer_id, 0)

    def _layer_index(self, layer_key):
        return self.layout.layer(self._layer_ids[layer_key], 0)

    def set_device_parameters(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_layer_ids(self):
        return dict(self._layer_ids)

    def _resolved_v_inner_length(self):
        return float(self.v_inner_length) if self.v_inner_length is not None else float(self.v_protrude_length) * 1.1

    def get_v_contact_x_positions(self, x=0.0):
        """Return centered V-pair positions; ``dist_v`` is the pair pitch."""
        if self.v_contact_pairs == 1:
            return [float(x)]
        center = (self.v_contact_pairs - 1) / 2.0
        return [float(x) + (index - center) * float(self.dist_v) for index in range(self.v_contact_pairs)]

    def get_v_outer_x_positions(self, x=0.0):
        """Spread probe pads while preserving order and the requested clearance."""
        if self.v_contact_pairs == 1:
            return [float(x)]
        # Backward compatibility: the original two-pair, single-exposure Hall
        # bar used the requested offsets verbatim.  Keep that familiar compact
        # layout; automatic pad spreading is for the new multi-pair/split modes.
        if self.v_contact_pairs == 2 and not self.split_ebl_exposure:
            offset = abs(float(self.v_outer_offset_x))
            return [float(x) - offset, float(x) + offset]
        configured_pitch = 2.0 * abs(float(self.v_outer_offset_x)) / (self.v_contact_pairs - 1)
        safe_pitch = float(self.v_outer_length) + self.outer_pad_gap
        pitch = max(configured_pitch, safe_pitch)
        center = (self.v_contact_pairs - 1) / 2.0
        return [float(x) + (index - center) * pitch for index in range(self.v_contact_pairs)]

    def _resolved_v_outer_offset_y(self):
        # Preserve the original default geometry exactly when the new EBL split
        # and variable-pair features are not in use.
        if self.v_contact_pairs == 2 and not self.split_ebl_exposure:
            return abs(float(self.v_outer_offset_y))

        required = (
            abs(float(self.i_outer_offset_y))
            + float(self.i_outer_width) / 2.0
            + float(self.v_outer_width) / 2.0
            + self.outer_pad_gap
        )
        contact_y = (float(self.bar_width) + float(self.v_protrude)) / 2.0
        if self.split_ebl_exposure:
            bridge_outer_y = (
                contact_y
                + float(self.v_inner_width) / 2.0
                + self.fine_fanout_length
                + self.bridge_pad_length
            )
            route_start_y = bridge_outer_y
        else:
            route_start_y = contact_y + float(self.v_inner_width) / 2.0

        # Leave an actual tapering run before the complete large-pad edge.
        # Merely separating pad rectangles creates needle-like polygons.
        if self.coarse_fanout_pad_edge_width > 0.0:
            landing_width = self.coarse_fanout_pad_edge_width
        else:
            chamfer_reduction = 2.0 * float(self.v_outer_chamfer) if self.v_outer_chamfer_type != 'none' else 0.0
            landing_width = max(float(self.v_outer_length) - chamfer_reduction, 0.0)
        start_width = self.bridge_pad_width if self.split_ebl_exposure else self._resolved_v_inner_length()
        minimum_taper_run = max(landing_width, start_width) + 5.0 * self.min_electrode_gap
        required = max(
            required,
            route_start_y + float(self.v_outer_width) / 2.0 + minimum_taper_run,
        )
        return max(abs(float(self.v_outer_offset_y)), required)

    def _resolved_i_outer_offset_x(self):
        requested = abs(float(self.i_outer_offset_x))
        if self.v_contact_pairs <= 2:
            return requested
        v_outermost = max(abs(position) for position in self.get_v_outer_x_positions(0.0))
        required = (
            v_outermost
            + float(self.v_outer_length) / 2.0
            + float(self.i_outer_length) / 2.0
            + self.outer_pad_gap
        )
        return max(requested, required)

    @staticmethod
    def _pad_edge_center(pad, edge):
        x, y = pad.center
        if edge == 'L':
            return x - pad.length / 2.0, y
        if edge == 'R':
            return x + pad.length / 2.0, y
        if edge == 'D':
            return x, y - pad.width / 2.0
        return x, y + pad.width / 2.0

    @staticmethod
    def _facing_edges(pad, target):
        """Return pad edges whose outward normal points toward ``target``."""
        dx = target.center[0] - pad.center[0]
        dy = target.center[1] - pad.center[1]
        edges = []
        if dx < -1e-9:
            edges.append('L')
        elif dx > 1e-9:
            edges.append('R')
        if dy < -1e-9:
            edges.append('D')
        elif dy > 1e-9:
            edges.append('U')
        return edges or ['L', 'R', 'D', 'U']

    @staticmethod
    def _edge_alignment_penalty(inner, outer, inner_edge, outer_edge):
        normals = {'L': (-1.0, 0.0), 'R': (1.0, 0.0), 'D': (0.0, -1.0), 'U': (0.0, 1.0)}
        dx = outer.center[0] - inner.center[0]
        dy = outer.center[1] - inner.center[1]
        length = max((dx * dx + dy * dy) ** 0.5, 1e-12)
        ux, uy = dx / length, dy / length
        in_normal = normals[inner_edge]
        out_normal = normals[outer_edge]
        inner_cosine = in_normal[0] * ux + in_normal[1] * uy
        outer_cosine = out_normal[0] * -ux + out_normal[1] * -uy
        return (1.0 - inner_cosine) + (1.0 - outer_cosine)

    @staticmethod
    def _polygon_region(polygon):
        region = db.Region()
        region.insert(polygon)
        return region

    @staticmethod
    def _minimum_polygon_angle(polygon):
        points = [(point.x, point.y) for point in polygon.each_point_hull()]
        if len(points) < 3:
            return 0.0
        angles = []
        for index, current in enumerate(points):
            previous = points[index - 1]
            following = points[(index + 1) % len(points)]
            first = (previous[0] - current[0], previous[1] - current[1])
            second = (following[0] - current[0], following[1] - current[1])
            denominator = math.hypot(*first) * math.hypot(*second)
            if denominator <= 1e-12:
                return 0.0
            cosine = (first[0] * second[0] + first[1] * second[1]) / denominator
            angles.append(math.degrees(math.acos(max(-1.0, min(1.0, cosine)))))
        return min(angles)

    def _clearance_region(self, region):
        half_gap = int(round(self.min_electrode_gap * GeometryUtils.UNIT_SCALE / 2.0))
        return region.sized(half_gap) if half_gap > 0 else region

    def _select_coarse_fanouts(self, routes):
        """Choose globally non-intersecting pad edges for all coarse routes.

        Candidate edges must face the destination.  A small constraint solver
        then chooses a collision-free set, ordered by shortest edge-to-edge
        distance and smallest polygon area.  This permits useful non-parallel
        pairs such as L-D or U-R instead of forcing U-D/L-R everywhere.
        """
        endpoint_regions = []
        for route_index, route in enumerate(routes):
            endpoint_regions.extend([
                (route_index, self._clearance_region(self._polygon_region(route['inner'].polygon))),
                (route_index, self._clearance_region(self._polygon_region(route['outer'].polygon))),
            ])

        domains = []
        for route_index, route in enumerate(routes):
            candidates = []
            inner = route['inner']
            outer = route['outer']
            for inner_edge in self._facing_edges(inner, outer):
                for outer_edge in self._facing_edges(outer, inner):
                    polygon = draw_trapezoidal_fanout(
                        inner,
                        outer,
                        inner_edge=inner_edge,
                        outer_edge=outer_edge,
                        outer_edge_width=(
                            self.coarse_fanout_pad_edge_width
                            if self.coarse_fanout_pad_edge_width > 0.0
                            else None
                        ),
                    )
                    region = self._polygon_region(polygon)
                    clearance_region = self._clearance_region(region)
                    if region.area() <= 0:
                        continue
                    minimum_angle = self._minimum_polygon_angle(polygon)
                    if minimum_angle < self.min_fanout_corner_angle:
                        continue
                    if any(
                        owner != route_index and (clearance_region & endpoint_region).area() > 0
                        for owner, endpoint_region in endpoint_regions
                    ):
                        continue
                    p1 = self._pad_edge_center(inner, inner_edge)
                    p2 = self._pad_edge_center(outer, outer_edge)
                    distance2 = (p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2
                    alignment_penalty = self._edge_alignment_penalty(
                        inner, outer, inner_edge, outer_edge
                    )
                    candidates.append({
                        'polygon': polygon,
                        'region': region,
                        'clearance_region': clearance_region,
                        'inner_edge': inner_edge,
                        'outer_edge': outer_edge,
                        'minimum_angle': minimum_angle,
                        # Prefer edges whose outward normals follow the route
                        # direction, then the shortest/smallest valid taper.
                        'score': (alignment_penalty, distance2, region.area()),
                    })
            candidates.sort(key=lambda candidate: candidate['score'])
            if not candidates:
                raise ValueError(f"No interference-free fanout edge pair for {route['name']}")
            domains.append(candidates)

        # Route the most constrained electrodes first.  Backtracking prevents
        # an early locally-short choice from blocking a later electrode.
        order = sorted(range(len(routes)), key=lambda index: (len(domains[index]), domains[index][0]['score']))
        selected = [None] * len(routes)
        selected_regions = []
        attempts = [0]

        def solve(depth):
            if depth == len(order):
                return True
            route_index = order[depth]
            for candidate in domains[route_index]:
                attempts[0] += 1
                if attempts[0] > 100000:
                    return False
                if any((candidate['clearance_region'] & occupied).area() > 0 for occupied in selected_regions):
                    continue
                selected[route_index] = candidate
                selected_regions.append(candidate['clearance_region'])
                if solve(depth + 1):
                    return True
                selected_regions.pop()
                selected[route_index] = None
            return False

        if not solve(0):
            raise ValueError(
                'Cannot find interference-free Hall bar fanouts; increase pad offsets/gaps '
                'or reduce pad dimensions'
            )

        self._last_fanout_edges = [
            {
                'name': route['name'],
                'inner_edge': candidate['inner_edge'],
                'outer_edge': candidate['outer_edge'],
                'minimum_angle': candidate['minimum_angle'],
            }
            for route, candidate in zip(routes, selected)
        ]
        return [candidate['polygon'] for candidate in selected]

    def _validate(self):
        positive = {
            'bar_length': self.bar_length,
            'bar_width': self.bar_width,
            'v_protrude_width': self.v_protrude,
            'v_protrude_length': self.v_protrude_length,
            'v_inner_width': self.v_inner_width,
            'v_outer_length': self.v_outer_length,
            'v_outer_width': self.v_outer_width,
            'i_inner_length': self.i_inner_length,
            'i_outer_length': self.i_outer_length,
            'i_outer_width': self.i_outer_width,
        }
        invalid = [name for name, value in positive.items() if float(value) <= 0.0]
        if invalid:
            raise ValueError('HallBar dimensions must be positive: ' + ', '.join(invalid))
        if self.v_contact_pairs < 1:
            raise ValueError('v_contact_pairs must be >= 1')
        if self.v_contact_pairs > 1 and float(self.dist_v) <= 0.0:
            raise ValueError('dist_v must be positive when v_contact_pairs > 1')
        if self.min_electrode_gap < 0.0:
            raise ValueError('min_electrode_gap cannot be negative')
        if self.outer_pad_gap < 0.0:
            raise ValueError('outer_pad_gap cannot be negative')
        if not (0.0 < self.min_fanout_corner_angle < 90.0):
            raise ValueError('min_fanout_corner_angle must be between 0 and 90 degrees')
        if self.coarse_fanout_pad_edge_width < 0.0:
            raise ValueError('coarse_fanout_pad_edge_width cannot be negative')

        v_inner_length = self._resolved_v_inner_length()
        if self.v_contact_pairs > 1 and float(self.dist_v) < v_inner_length + self.min_electrode_gap:
            raise ValueError('dist_v is too small: adjacent V channel contacts would interfere')

        outermost = max(abs(position) for position in self.get_v_contact_x_positions(0.0))
        v_half_length = max(float(self.v_protrude_length), v_inner_length) / 2.0
        usable_half_length = float(self.bar_length) / 2.0 - float(self.i_inner_length) / 2.0
        if outermost + v_half_length + self.min_electrode_gap > usable_half_length:
            raise ValueError(
                'V contacts do not fit between the I contacts; increase bar_length, '
                'reduce dist_v/v_contact_pairs, or reduce contact dimensions'
            )

        if self.split_ebl_exposure:
            if not (11 <= self._layer_ids['source_drain'] <= 19):
                raise ValueError('split EBL coarse source_drain_layer_id must be in 11-19')
            if self._layer_ids['fine_source_drain'] != self._layer_ids['source_drain'] + 10:
                raise ValueError('split EBL fine layer must equal the coarse layer + 10 (21-29)')
            if self.fine_fanout_length < 0.0 or self.ebl_overlap <= 0.0:
                raise ValueError('fine_fanout_length cannot be negative and ebl_overlap must be positive')
            if self.bridge_pad_length <= 0.0 or self.bridge_pad_width <= 0.0:
                raise ValueError('bridge pad dimensions must be positive')
            if self.ebl_overlap > self.bridge_pad_length:
                raise ValueError('ebl_overlap cannot exceed bridge_pad_length')
            if self.v_contact_pairs > 1 and float(self.dist_v) < self.bridge_pad_width + self.min_electrode_gap:
                raise ValueError('dist_v is too small: adjacent V bridge pads would interfere')

    def _append_text_shape(self, text, x, y, layer_key):
        if not text:
            return []
        text = str(text)
        try:
            polygons = TextUtils.create_text_deplof(
                text=text,
                x=x,
                y=y,
                size_um=self.label_size,
                anchor='left_bottom',
                justify='left',
            )
            if polygons:
                return polygons
        except Exception:
            pass

        try:
            generator = pya.TextGenerator.default_generator()
            mag = float(self.label_size) / max(generator.dheight(), 1e-9)
            region = generator.text(text, PROCESS_CONFIG["dbu"], mag, False, 0.0, 0.0, 0.0).merged()
            bbox = region.bbox()
            dx = int(round(x / PROCESS_CONFIG["dbu"] - bbox.left))
            dy = int(round(y / PROCESS_CONFIG["dbu"] - bbox.bottom))
            return [region.moved(dx, dy)]
        except Exception:
            return [pya.Text(text, int(x * 1000), int(y * 1000))]

    def _append_note_text(self, text, x, y):
        if not text:
            return []
        return [pya.Text(str(text), int(x * 1000), int(y * 1000))]

    def _normalized_mark_type(self, mark_type):
        aliases = {
            "l": "l_shape",
            "L_shape": "l_shape",
            "t": "t_shape",
            "T_shape": "t_shape",
        }
        return aliases.get(str(mark_type), mark_type)

    def _create_mark(self, x, y, mark_type, rotation):
        normalized = self._normalized_mark_type(mark_type)
        stroke_ratio = max(self.mark_width / max(self.mark_size, 1e-9), 1e-3)

        if normalized == "sq_missing":
            return MarkUtils.sq_missing(x, y, self.mark_size).rotate(rotation)
        if normalized in ("l_shape", "t_shape", "cross_tri"):
            return getattr(MarkUtils, normalized)(x, y, self.mark_size, stroke_ratio).rotate(rotation)
        if normalized in ("square", "circle", "diamond"):
            return getattr(MarkUtils, normalized)(x, y, self.mark_size).rotate(rotation)
        if normalized == "triangle":
            return MarkUtils.triangle(x, y, self.mark_size).rotate(rotation)
        if hasattr(MarkUtils, normalized):
            try:
                return getattr(MarkUtils, normalized)(x, y, self.mark_size, self.mark_width).rotate(rotation)
            except TypeError:
                return getattr(MarkUtils, normalized)(x, y, self.mark_size).rotate(rotation)
        return MarkUtils.cross(x, y, self.mark_size, self.mark_width).rotate(rotation)

    def create_bar(self, cell, x=0.0, y=0.0):
        self._validate()
        layer_id = self._layer_index('channel')
        # 沟道主区
        bar = GeometryUtils.create_rectangle(
            x, y, self.bar_length, self.bar_width, center=True
        )
        cell.shapes(layer_id).insert(bar)
        # V区突出
        protrude = self.v_protrude
        v_w = self.bar_width + protrude * 2
        v_len = self.v_protrude_length
        for contact_x in self.get_v_contact_x_positions(x):
            protrusion = GeometryUtils.create_rectangle(contact_x, y, v_len, v_w, center=True)
            cell.shapes(layer_id).insert(protrusion)

    def create_contacts(self, cell, x=0.0, y=0.0):
        self._validate()
        coarse_layer = self._layer_index('source_drain')
        fine_layer = self._layer_index('fine_source_drain')
        coarse_routes = []

        def insert_contact(name, inner, outer, inner_edge, outer_edge, direction, bridge_orientation):
            target_inner_layer = fine_layer if self.split_ebl_exposure else coarse_layer
            cell.shapes(target_inner_layer).insert(inner.polygon)
            cell.shapes(coarse_layer).insert(outer.polygon)

            if not self.split_ebl_exposure:
                coarse_routes.append({'name': name, 'inner': inner, 'outer': outer})
                return

            dx, dy = direction
            if bridge_orientation == 'horizontal':
                inner_boundary = inner.center[0] + dx * inner.length / 2.0
                bridge_inner = inner_boundary + dx * self.fine_fanout_length
                bridge_center = (bridge_inner + dx * self.bridge_pad_length / 2.0, inner.center[1])
                bridge = draw_pad(bridge_center, self.bridge_pad_length, self.bridge_pad_width)
                transition_center = (bridge_inner + dx * self.ebl_overlap / 2.0, inner.center[1])
                transition = draw_pad(transition_center, self.ebl_overlap, self.bridge_pad_width)
            else:
                inner_boundary = inner.center[1] + dy * inner.width / 2.0
                bridge_inner = inner_boundary + dy * self.fine_fanout_length
                bridge_center = (inner.center[0], bridge_inner + dy * self.bridge_pad_length / 2.0)
                bridge = draw_pad(bridge_center, self.bridge_pad_width, self.bridge_pad_length)
                transition_center = (inner.center[0], bridge_inner + dy * self.ebl_overlap / 2.0)
                transition = draw_pad(transition_center, self.bridge_pad_width, self.ebl_overlap)

            cell.shapes(coarse_layer).insert(bridge.polygon)
            cell.shapes(fine_layer).insert(
                draw_trapezoidal_fanout(inner, transition, inner_edge=inner_edge, outer_edge=outer_edge)
            )
            if self.ebl_overlap > 0.0:
                cell.shapes(fine_layer).insert(transition.polygon)
            coarse_routes.append({'name': name, 'inner': bridge, 'outer': outer})
        # I电极
        I_contacts = [
            ("I_source", (x - self.bar_length/2, y), "left"),
            ("I_drain", (x + self.bar_length/2, y), "right"),
        ]
        i_inner_width = self.i_inner_width if self.i_inner_width is not None else self.bar_width * 1.1
        i_outer_offset_x = self._resolved_i_outer_offset_x()
        for name, (cx, cy), direction in I_contacts:
            inner = draw_pad((cx, cy), self.i_inner_length, i_inner_width, chamfer_size=0, chamfer_type='none')
            if direction == "left":
                outer_center = (x - i_outer_offset_x, y + self.i_outer_offset_y)
                inner_edge, outer_edge, vector = 'L', 'R', (-1.0, 0.0)
            else:
                outer_center = (x + i_outer_offset_x, y + self.i_outer_offset_y)
                inner_edge, outer_edge, vector = 'R', 'L', (1.0, 0.0)
            outer = draw_pad(outer_center, self.i_outer_length, self.i_outer_width, chamfer_size=self.i_outer_chamfer, chamfer_type=cast(Literal['none', 'straight', 'round'], self.i_outer_chamfer_type))
            insert_contact(name, inner, outer, inner_edge, outer_edge, vector, 'horizontal')
            if self.electrode_text_label:
                for shape in self._append_text_shape(name, outer_center[0], outer_center[1], 'labels'):
                    cell.shapes(self._layer_index('labels')).insert(shape)
        # V电极
        V_contacts = []
        outer_xs = self.get_v_outer_x_positions(x)
        outer_y = self._resolved_v_outer_offset_y()
        contact_y = (self.bar_width + self.v_protrude) / 2.0
        for index, (contact_x, outer_x) in enumerate(zip(self.get_v_contact_x_positions(x), outer_xs), start=1):
            V_contacts.extend([
                (f"V{index}_pos", (contact_x, y + contact_y), "top", (outer_x, y + outer_y)),
                (f"V{index}_neg", (contact_x, y - contact_y), "bottom", (outer_x, y - outer_y)),
            ])
        v_inner_length = self._resolved_v_inner_length()
        for name, (cx, cy), direction, (lx, ly) in V_contacts:
            inner = draw_pad((cx, cy), v_inner_length, self.v_inner_width, chamfer_size=0, chamfer_type='none')
            outer_center = (lx, ly)
            outer = draw_pad(outer_center, self.v_outer_length, self.v_outer_width, chamfer_size=self.v_outer_chamfer, chamfer_type=cast(Literal['none', 'straight', 'round'], self.v_outer_chamfer_type))
            if direction == 'top':
                inner_edge, outer_edge, vector = 'U', 'D', (0.0, 1.0)
            else:
                inner_edge, outer_edge, vector = 'D', 'U', (0.0, -1.0)
            insert_contact(name, inner, outer, inner_edge, outer_edge, vector, 'vertical')
            if self.electrode_text_label:
                for shape in self._append_text_shape(name, outer_center[0], outer_center[1], 'labels'):
                    cell.shapes(self._layer_index('labels')).insert(shape)

        for fanout in self._select_coarse_fanouts(coarse_routes):
            cell.shapes(coarse_layer).insert(fanout)

    def create_alignment_marks(self, cell, x=0.0, y=0.0):
        layer_id = self._layer_index('alignment_marks')
        device_width = self.device_margin_x * 2
        device_height = self.device_margin_y * 2
        mark_positions = [
            (x - device_width/2, y + device_height/2),
            (x + device_width/2, y + device_height/2),
            (x - device_width/2, y - device_height/2),
            (x + device_width/2, y - device_height/2)
        ]
        for i, (mark_x, mark_y) in enumerate(mark_positions):
            mark_type = self.mark_types[i] if i < len(self.mark_types) else 'cross'
            rotation = self.mark_rotations[i] if i < len(self.mark_rotations) else 0
            marks = self._create_mark(mark_x, mark_y, mark_type, rotation)
            shapes = marks.get_shapes() if hasattr(marks, 'get_shapes') else [marks]
            if isinstance(shapes, list):
                for shape in shapes:
                    cell.shapes(layer_id).insert(shape)
            else:
                cell.shapes(layer_id).insert(shapes)

    def create_device_label(self, cell, x, y, label_text="HallBar", anchor="center"):
        layer_id = self._layer_index('labels')
        if anchor == "topleft_mark":
            label_x = x - self.device_margin_x + self.label_offset_x
            label_y = y + self.device_margin_y + self.label_offset_y
        else:
            label_x = x + self.label_offset_x
            label_y = y + self.label_offset_y
        text_shapes = self._append_text_shape(label_text, label_x, label_y, 'labels')
        for shape in text_shapes:
            cell.shapes(layer_id).insert(shape)

    def create_single_device(self, cell_name="HallBar_Device", x=0, y=0, label_text="HallBar", show_param_label=True):
        cell = self.layout.create_cell(cell_name)
        x = float(x)
        y = float(y)
        self.create_bar(cell, x, y)
        self.create_contacts(cell, x, y)
        self.create_alignment_marks(cell, x, y)
        self.create_device_label(cell, x, y, label_text, anchor="topleft_mark")
        # 在左下角mark的右上角offset(+10, +10)处标注参数
        if show_param_label:
            # 左下角mark中心
            mark_x = x - self.device_margin_x
            mark_y = y - self.device_margin_y
            label_x = mark_x + 10
            label_y = mark_y + 10
            param_text = f"W={self.bar_width:.2f}, L={self.bar_length:.2f}, VP={self.v_protrude_length:.2f}, NV={self.v_contact_pairs}"
            if self.split_ebl_exposure:
                param_text += f", EBL={self._layer_ids['source_drain']}/{self._layer_ids['fine_source_drain']}"
            layer_id = self._layer_index('parameter_labels')
            for shape in self._append_note_text(param_text, label_x, label_y):
                cell.shapes(layer_id).insert(shape)
        return cell

    def create_device_array(self, rows=4, cols=4, device_spacing_x=None, device_spacing_y=None, label_prefix="HB"):
        if device_spacing_x is None:
            device_spacing_x = self.device_margin_x * 2 + 50
        if device_spacing_y is None:
            device_spacing_y = self.device_margin_y * 2 + 50
        array_cell = self.layout.create_cell("HallBar_Array")
        device_id = 1
        label_layer = self._layer_index('labels')
        label_offset_x = 20.0  # um
        label_offset_y = -20.0 # um
        for row in range(rows):
            for col in range(cols):
                device_x = int(col * device_spacing_x)
                device_y = int(row * device_spacing_y)
                # Excel格式label
                excel_label = f"{chr(ord('A') + col)}{row + 1}"
                # 生成单元器件
                device_cell = self.create_single_device(
                    f"HallBar_{device_id:03d}",
                    device_x, device_y, excel_label, show_param_label=False
                )
                array_cell.insert(db.CellInstArray(
                    device_cell.cell_index(),
                    db.Trans(0, 0)
                ))
                # 左上角mark中心
                mark_x = device_x - self.device_margin_x
                mark_y = device_y + self.device_margin_y
                # 插入label（右下角偏移）
                for shape in self._append_text_shape(excel_label, mark_x + label_offset_x, mark_y + label_offset_y, 'labels'):
                    array_cell.shapes(label_layer).insert(shape)
                device_id += 1
        return array_cell 

    def scan_parameters_and_create_array(self, param_ranges, rows=3, cols=3, offset_x=0, offset_y=0, show_param_label=True):
        """
        扫描参数并创建参数变化的器件阵列
        param_ranges: {'param_name': [min, max, steps]}
        rows, cols: 阵列行列数
        offset_x, offset_y: 阵列起始坐标偏移
        show_param_label: 是否显示参数标注（KLayout text）
        """
        scan_cell = self.layout.create_cell("HallBar_Parameter_Scan")
        # 计算参数步长
        param_steps = {}
        for param_name, param_range in param_ranges.items():
            if len(param_range) == 3:
                min_val, max_val, steps = param_range
                param_steps[param_name] = (max_val - min_val) / (steps - 1) if steps > 1 else 0
            else:
                param_steps[param_name] = 0
        device_spacing_x = self.device_margin_x * 2 + 50
        device_spacing_y = self.device_margin_y * 2 + 50
        device_id = 1
        for row in range(rows):
            for col in range(cols):
                current_params = {}
                # 行扫描
                if 'bar_width' in param_ranges:
                    min_val, max_val, steps = param_ranges['bar_width']
                    bar_width = min_val + row * (max_val - min_val) / (steps - 1)
                    current_params['bar_width'] = bar_width
                # 列扫描
                if 'bar_length' in param_ranges:
                    min_val, max_val, steps = param_ranges['bar_length']
                    bar_length = min_val + col * (max_val - min_val) / (steps - 1)
                    current_params['bar_length'] = bar_length
                # 其它参数扫描
                if 'v_protrude_length' in param_ranges:
                    min_val, max_val, steps = param_ranges['v_protrude_length']
                    v_protrude_length = min_val + row * (max_val - min_val) / (steps - 1)
                    current_params['v_protrude_length'] = v_protrude_length
                self.set_device_parameters(**current_params)
                device_x = int(offset_x + col * device_spacing_x)
                device_y = int(offset_y + row * device_spacing_y)
                # Excel格式角标
                excel_label = f"{chr(ord('A') + col)}{row + 1}"
                cell_name = f"HB_SCAN_{device_id:02d}"
                dev_cell = self.create_single_device(cell_name, device_x, device_y, excel_label, show_param_label=show_param_label)
                scan_cell.insert(db.CellInstArray(dev_cell.cell_index(), db.Trans(0, 0)))
                device_id += 1
        return scan_cell


def main():
    """主函数 - 用于测试HallBar器件生成"""
    # 创建HallBar器件实例
    hallbar = HallBar()

    # 设置器件参数
    hallbar.set_device_parameters(
        bar_length=60.0,   # Hall bar长度 60μm
        bar_width=12.0,    # Hall bar宽度 12μm
    )

    # 创建单个器件进行测试
    print("创建单个HallBar器件...")
    single_device = hallbar.create_single_device("Test_HallBar", 0, 0, "Test_HallBar")
    print(f"单个器件已创建: {single_device.name}")

    # 创建4x4器件阵列
    print("创建4x4 HallBar器件阵列...")
    device_array = hallbar.create_device_array(rows=4, cols=4)
    print(f"器件阵列已创建: {device_array.name}")

    # 优雅的参数扫描测试
    print("参数扫描测试：批量生成不同参数的HallBar器件...")
    param_ranges = {
        'bar_width': [8.0, 16.0, 9],    # 行扫描
        'bar_length': [40.0, 80.0, 9],  # 列扫描
        'v_protrude_length': [4.0, 8.0, 4],
    }
    scan_cell = hallbar.scan_parameters_and_create_array(param_ranges, rows=9, cols=9, offset_x=0, offset_y=0)
    print(f"参数扫描器件已创建: {scan_cell.name}")

    # 保存布局文件
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from config import get_gds_path
    
    output_file = get_gds_path("TEST_HALLBAR_COMP.gds")
    hallbar.layout.write(output_file)
    print(f"布局文件已保存: {output_file}")

    print("HallBar器件生成测试完成！")


if __name__ == "__main__":
    main() 
