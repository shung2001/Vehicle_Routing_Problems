import math
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from Hexagon_cell import HexGrid


def hex_corners(center_x, center_y, size=1.0):
    corners = []
    for i in range(6):
        angle_deg = 60 * i + 30   # pointy-top
        angle_rad = math.radians(angle_deg)
        x = center_x + size * math.cos(angle_rad)
        y = center_y + size * math.sin(angle_rad)
        corners.append((x, y))
    return corners


def plot_hex_grid_style():
    grid = HexGrid(radius=2)
    size = 1.0

    # 예시 설정
    origin = (2, -1)
    destination = (-1, 1)

    obstacles = {
        (0, 2),
        (1, 0),
        (1, -1),
        (2, -1)
    }

    highlighted = {
        (0, 1),
        (1, 1),
        (0, 0),
        (-1, 0),
        (-1, 1)
    }

    fig, ax = plt.subplots(figsize=(7, 7))

    for cell in grid.cells:
        cx, cy = grid.axial_to_pixel(cell, size)
        corners = hex_corners(cx, cy, size)

        # 기본 색
        facecolor = "lightgray"
        edgecolor = "white"
        linewidth = 1.0

        # 장애물
        if cell in obstacles:
            facecolor = "black"
            edgecolor = "black"

        # 강조 영역
        elif cell in highlighted:
            facecolor = "#d9dcf5"   # 연한 보라/파랑 느낌
            edgecolor = "#6b7cff"

        hex_patch = Polygon(
            corners,
            closed=True,
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=linewidth
        )
        ax.add_patch(hex_patch)

    # origin / destination 점과 텍스트
    ox, oy = grid.axial_to_pixel(origin, size)
    dx, dy = grid.axial_to_pixel(destination, size)

    ax.plot(ox, oy, 's', markersize=5, color='red')
    ax.text(ox + 0.2, oy + 0.25, "Origin", color='red', fontsize=11)

    ax.plot(dx, dy, 's', markersize=5, color='red')
    ax.text(dx - 0.8, dy - 0.45, "Destination", color='red', fontsize=11)

    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_hex_grid_style()