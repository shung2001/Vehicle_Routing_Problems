import math

HEX_DIRECTIONS = [
    (1, 0), (1, -1), (0, -1),
    (-1, 0), (-1, 1), (0, 1)
]

class HexGrid:
    def __init__(self, radius):
        self.radius = radius
        self.cells = self.generate_hex_cells()

    def generate_hex_cells(self):
        cells = []
        for q in range(-self.radius, self.radius + 1):
            r1 = max(-self.radius, -q - self.radius)
            r2 = min(self.radius, -q + self.radius)
            for r in range(r1, r2 + 1):
                cells.append((q, r))
        return cells

    def get_neighbors(self, cell):
        q, r = cell
        neighbors = []
        for dq, dr in HEX_DIRECTIONS:
            nxt = (q + dq, r + dr)
            if nxt in self.cells:
                neighbors.append(nxt)
        return neighbors

    def axial_to_pixel(self, cell, size=1.0):
        q, r = cell
        x = size * (3/2 * q)
        y = size * (math.sqrt(3) * (r + q/2))
        return (x, y)