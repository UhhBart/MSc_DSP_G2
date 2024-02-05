import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, shape, box, Point
import json

def calculate_bounding_box(feature_collection):
    min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')

    for feature in feature_collection['features']:
        bounds = shape(feature['geometry']).bounds

        min_x = min(min_x, bounds[0])
        min_y = min(min_y, bounds[1])
        max_x = max(max_x, bounds[2])
        max_y = max(max_y, bounds[3])

    # Create a bounding box polygon using the min and max coordinates
    # bounding_box = box(min_x, min_y, max_x, max_y)

    return (min_x, min_y, max_x, max_y)


GRID_SIZE = 200
def create_grid_gdf(bounding_box):
    amsterdam_lat = 52.32

    amsterdam_bbox = bounding_box

    # Calculate grid bounds
    lat_step = (GRID_SIZE / 111000) / np.cos(np.radians(amsterdam_lat))  # Correct for latitude
    lon_step = GRID_SIZE / 111000  # 1 degree of longitude is approximately 111 kilometers

    grid_polygons = []
    for lat in np.arange(amsterdam_bbox[0], amsterdam_bbox[2], lat_step):
        for lon in np.arange(amsterdam_bbox[1], amsterdam_bbox[3], lon_step):
            # polygon = Polygon([
            #     (lon, lat),
            #     (lon + lon_step, lat),
            #     (lon + lon_step, lat + lat_step),
            #     (lon, lat + lat_step),
            #     (lon, lat),
            # ])
            polygon = box(lon, lat, lon + lon_step, lat + lat_step,)

            grid_polygons.append(polygon)

    grid_gdf = gpd.GeoDataFrame(geometry=grid_polygons, crs="EPSG:4326")
    return grid_gdf


def check_overlap_percentage(large_polygon_coords, small_polygon_coords):
    # Create Shapely Polygon objects from the coordinates
    large_polygon = Polygon(large_polygon_coords)
    small_polygon = Polygon(small_polygon_coords)

    # Check if at least 50% of the small polygon is inside/overlaps with the large polygon
    intersection = large_polygon.intersection(small_polygon)
    overlap = intersection.area / small_polygon.area

    return overlap >= 0.5

service_areas = json.load(open('src/service_areas.geojson'))
bounding_box = calculate_bounding_box(service_areas)
print(bounding_box)
grid_gdf = create_grid_gdf(bounding_box)

# Switch the order to (latitude, longitude) for each polygon
grid_gdf['geometry'] = grid_gdf['geometry'].apply(lambda geom: geom.exterior.coords.xy[::-1])
grid_gdf['geometry'] = grid_gdf['geometry'].apply(lambda coords: Polygon(zip(coords[0], coords[1])))

grid_gdf['service_area'] = pd.Series([None] * len(grid_gdf), index=grid_gdf.index)
grid_gdf = grid_gdf[['service_area', 'geometry']]

print(grid_gdf.size)
for i, row in grid_gdf.iterrows():
    for feature in service_areas['features']:
        service_area = shape(feature['geometry'])
        intersection = service_area.intersection(row['geometry'])
        if (intersection.area / row['geometry'].area) >= 0.5:
            grid_gdf.loc[i, 'service_area'] = feature['properties']['name']
            break

# Adding zipcodes to existing grid file.
# from shapely.wkt import loads
# zipcodes = json.load(open('zipcodes.geojson'))
# grid_df = pd.read_csv('grid_by_hand.csv', sep=",", encoding="utf-8")
# grid_df['geometry'] = grid_df['geometry'].apply(loads)
# grid_gdf = gpd.GeoDataFrame(grid_df, geometry='geometry', crs='EPSG:4326')
# # pc4_code

# grid_gdf.drop(columns=['Unnamed: 0'], inplace=True)
# print(grid_gdf.columns)
# print(grid_gdf.size)
# for i, row in grid_gdf.iterrows():
#     for feature in zipcodes['features']:
#         zipcode = shape(feature['geometry'])
#         intersection = zipcode.intersection(row['geometry'])
#         if (intersection.area / row['geometry'].area) >= 0.5:
#             grid_gdf.loc[i, 'zipcode'] = feature['properties']['pc4_code']
#             break

grid_gdf.to_csv('test_grids2.csv')
