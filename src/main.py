from Hexagon_cell import HexGrid

grid = HexGrid(radius=2)

print("전체 셀:", grid.cells)
print("중심 이웃:", grid.get_neighbors((0, 0)))

for cell in grid.cells:
    print(cell, "->", grid.axial_to_pixel(cell))