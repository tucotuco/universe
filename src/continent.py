import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import Voronoi
import random
from shapely.geometry import Polygon, Point
import geopandas as gpd

def generate_non_degenerate_voronoi(num_plates, map_size):
    while True:
        # Step 1: Place random points on the map
        plate_points = np.random.randint(0, map_size, size=(num_plates, 2))

        # Step 2: Create Voronoi polygons to define plate boundaries
        vor = Voronoi(plate_points)

        # Step 3: Check for degenerate cells
        degenerate = True
        for region in vor.regions:
            if -1 not in region and len(region) > 0:
                polygon_points = [vor.vertices[i] for i in region]
                polygon = Polygon(polygon_points)
                if polygon.is_empty or polygon.area < 1e-5:
                    degenerate = False
                    break

        if not degenerate:
            break

    # Step 4: Store plate information in a dictionary
    plate_info = {}

    for i, region in enumerate(vor.regions):
        if -1 not in region and len(region) > 0:
            # Convert Voronoi region into a Shapely Polygon
            polygon_points = [vor.vertices[i] for i in region]
            polygon = Polygon(polygon_points)

            # Generate a random color for visualization
            color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

            # Find the center of the plate
            center_x = np.mean([p[0] for p in polygon_points])
            center_y = np.mean([p[1] for p in polygon_points])

            # Store plate information
            plate_info[f"Plate {i}"] = {
                "x": center_x,
                "y": center_y,
                "polygon": polygon,
                "color": color
            }

    return plate_info

# Step 5: Visualize the polygons with distinct random colors and display the plate count
def visualize_plates(plate_info, num_plates, map_size):
    fig, ax = plt.subplots(figsize=(8, 8))

    for plate, info in plate_info.items():
        gdf = gpd.GeoDataFrame({'geometry': [info["polygon"]]})
        gdf.plot(ax=ax, color=info["color"], label=plate)

    # Display all centers as black circles with a radius of 3 pixels
    all_centers_x = [info["x"] for info in plate_info.values()]
    all_centers_y = [info["y"] for info in plate_info.values()]
    plt.scatter(all_centers_x, all_centers_y, c="black", s=9, marker="o")

    # Display the plate count in the title
    plt.xlim(0, map_size)
    plt.ylim(0, map_size)
    plt.legend()
    plt.title(f"Tectonic Plates (n={num_plates}) with Voronoi Boundaries and Centers")
    plt.show()

if __name__ == "__main__":
    num_plates = 5  # Adjust the number of plates
    map_size = 100  # Adjust the size of the map

    plate_info = generate_non_degenerate_voronoi(num_plates, map_size)
    visualize_plates(plate_info, num_plates, map_size)

# import random
# import numpy as np
# import matplotlib.pyplot as plt
# 
# def generate_continent_map(size, num_iterations, seed=None):
#     if seed is not None:
#         np.random.seed(seed)
# 
#     # Initialize the map with random values
#     map_data = np.random.rand(size, size)
# 
#     # Apply smoothing using a simple cellular automaton
#     for _ in range(num_iterations):
#         for i in range(1, size - 1):
#             for j in range(1, size - 1):
#                 neighbors = map_data[i - 1:i + 2, j - 1:j + 2]
#                 avg = np.mean(neighbors)
#                 map_data[i, j] = avg
# 
#     return map_data
# 
# def visualize_map(map_data):
#     plt.imshow(map_data, cmap='terrain', interpolation='bilinear')
#     plt.colorbar()
#     plt.show()
# 
# if __name__ == "__main__":
#     size = 100  # Adjust the size of the map
#     num_iterations = 10  # Adjust the number of smoothing iterations
#     seed = random.randint(0, 999999)
# #    seed = 42  # Change the seed for reproducibility
# 
#     continent_map = generate_continent_map(size, num_iterations, seed)
#     visualize_map(continent_map)
