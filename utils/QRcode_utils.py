# -*- coding: utf-8 -*-
"""
二维码工具模块 - 生成二维码图案并转换为KLayout多边形
"""

import qrcode
import numpy as np
from utils.geometry import GeometryUtils

class QRCodeUtils:
    """二维码工具类"""
    @staticmethod
    def generate_qr_matrix(data, version=1, box_size=10, border=4):
        """
        生成二维码矩阵（黑白像素阵列）
        :param data: 要编码的数据
        :param version: 二维码版本（1-40）
        :param box_size: 每个像素的大小（用于后续多边形尺寸）
        :param border: 边框宽度（像素）
        :return: numpy.ndarray, dtype=bool
        """
        qr = qrcode.QRCode(
            version=version,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        return np.array(matrix, dtype=bool)

    @staticmethod
    def qr_matrix_to_polygons(matrix, x0=0, y0=0, box_size=1):
        """
        将二维码矩阵转换为KLayout多边形列表（每个黑色像素一个小正方形）
        :param matrix: 二维bool数组，True为黑色模块
        :param x0: 左上角x坐标（um）
        :param y0: 左上角y坐标（um）
        :param box_size: 每个像素的边长（um）
        :return: List[Polygon]
        """
        polys = []
        n_rows, n_cols = matrix.shape
        for i in range(n_rows):
            for j in range(n_cols):
                if matrix[i, j]:
                    # 左上为(0,0)，y向下
                    x = x0 + j * box_size
                    y = y0 - i * box_size
                    poly = GeometryUtils.create_rectangle(x + box_size/2, y - box_size/2, box_size, box_size, center=True)
                    polys.append(poly)
        return polys

if __name__ == "__main__":
    # 测试二维码生成与多边形转换
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    try:
        import pya
        Layout = pya.Layout
    except (ImportError, AttributeError):
        import klayout.db as pya
        Layout = pya.Layout
    from config import LAYER_DEFINITIONS
    from utils.geometry import GeometryUtils

    # 设置单位缩放
    unit_scale = 1000  # 1um = 1000dbu
    GeometryUtils.UNIT_SCALE = unit_scale

    # 生成二维码矩阵
    data = "https://www.example.com"
    matrix = QRCodeUtils.generate_qr_matrix(data, version=2, box_size=1, border=4)
    box_size = 4  # 每个像素10um

    # 转换为多边形
    polys = QRCodeUtils.qr_matrix_to_polygons(matrix, x0=0, y0=0, box_size=box_size)

    # 创建layout并插入多边形
    layout = Layout()
    layout.dbu = 0.001  # 1nm per dbu
    cell = layout.create_cell("QR_TEST")
    # 需在config.py中定义'labels'层
    from config import LAYER_DEFINITIONS
    layer_info = LAYER_DEFINITIONS['labels']
    layer = layout.layer(layer_info['id'], 0, layer_info['name'])
    for poly in polys:
        cell.shapes(layer).insert(poly)
    layout.write('TEST_QRCODE_UTILS.gds')
    print('二维码GDS文件 TEST_QRCODE_UTILS.gds 已生成。') 