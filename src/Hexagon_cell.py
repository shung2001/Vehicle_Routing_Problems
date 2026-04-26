import h3
import matplotlib.pyplot as plt

geo = {
    "type": "Polygon",
    "coordinates": [[
        [126.6, 37.3],
        [127.3, 37.3],
        [127.3, 37.8],
        [126.6, 37.8],
        [126.6, 37.3]
    ]]
}

resolution = 7
h3_cells = h3.geo_to_cells(geo, resolution)

fig, ax = plt.subplots(figsize=(8, 8))

for cell in h3_cells:
    boundary = h3.cell_to_boundary(cell)
    xs = [lng for lat, lng in boundary]
    ys = [lat for lat, lng in boundary]
    ax.fill(xs, ys, edgecolor="black", linewidth=0.3, alpha=0.6)

ax.set_aspect("equal")
ax.set_title(f"H3 grid, res={resolution}")
plt.show()