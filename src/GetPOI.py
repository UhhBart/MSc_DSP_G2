import pandas as pd
import numpy as np
import geopandas as gpd
import osmnx as ox
from scipy.spatial import cKDTree
from shapely.wkt import loads

GRID_PATH = "final_data/grids/grid_by_hand.csv"

# CRS_AMSTERDAM = "EPSG:28992"

class GetPoiDistances():
    def __init__(
        self,
        poi_types=['university', 'school', 'kindergarten', 'college', 'childcare', 'health_centre', 'hospital', 'nursing_home'],
        meters=250,
        grid_path = GRID_PATH
    ) -> None:

        self.poi_types = poi_types
        self.meters = meters

        self.grid_df = pd.read_csv(grid_path, sep=",", encoding="utf-8")

        self.grid_df['geometry'] = self.grid_df['geometry'].apply(loads)
        self.grid_gdf = gpd.GeoDataFrame(self.grid_df, geometry='geometry', crs='EPSG:4326')

        self.prio_pois_df = gpd.GeoDataFrame()

    def get_distances(
        self,
        city_name = "Amsterdam",
        poi_type = "amenity"
    ):

        amenities = self.get_pois(city_name, poi_type)

        self.prio_pois_df = amenities[amenities.amenity.isin(self.poi_types)][['amenity', 'geometry']]
        # self.prio_pois_df = self.prio_pois_df.set_crs(CRS_AMSTERDAM, allow_override=True)
        self.grid_gdf = self.grid_gdf.to_crs('EPSG:4326')

        buffer_num = self.meters * (1 / 68000.09)
        self.grid_gdf['buffer'] = self.grid_gdf.geometry.buffer(buffer_num, resolution=16)


        # Check for invalid types
        if not self.grid_gdf.geometry.is_valid.all() or not self.prio_pois_df.geometry.is_valid.all():
            raise ValueError("Invalid geometries found in one or more GeoDataFrames.")

        # Build KD tree
        poi_coordinates = self.prio_pois_df.geometry.apply(lambda geom: (geom.centroid.x, geom.centroid.y)).tolist()
        self.poi_tree = cKDTree(poi_coordinates)

        self.grid_gdf[['distances', 'poi_indices']] = self.grid_gdf.apply(self.calculate_distances_within_buffer, axis=1, result_type='expand')

        self.grid_gdf['summed_distance'] = [sum(x) if isinstance(x, np.ndarray) or isinstance(x, list) else x for x in self.grid_gdf['distances']]

        return self.grid_gdf

    def get_pois(
        self,
        city,
        poi_type
    ):
        """
        Fetch points of interest of a specific type in a given city.

        Args:
        city (str): Name of the city.
        poi_type (str): Type of point of interest.

        Returns:
        GeoDataFrame: A GeoDataFrame containing points of interest.
        """
        # Define the query for the specified city
        place_query = {"city": city, "country": "Netherlands"}

        # Retrieve POIs
        pois = ox.features_from_place(place_query, tags={poi_type: True})

        return pois


    def calculate_distances_within_buffer(
            self,
            row
        ):
            buffer = row.buffer
            nearby_pois = self.prio_pois_df[self.prio_pois_df.geometry.within(buffer)]

            if len(nearby_pois) > 0:
                poi_coordinates = nearby_pois.geometry.apply(lambda geom: (geom.centroid.x, geom.centroid.y)).tolist()
                poi_tree = cKDTree(poi_coordinates)
                grid_centroid = row.geometry.centroid
                distances, poi_indices = poi_tree.query((grid_centroid.x, grid_centroid.y), k=len(nearby_pois))
                return distances, poi_indices
            else:
                return [], []
