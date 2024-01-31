import streamlit as st
import numpy as np
import pandas as pd
import json
import shapely.geometry
from shapely import wkt, reverse

FILE_NAME = 'grid_final'

def wkt_to_geojson(wkt_string):
    # Parse WKT string to Shapely geometry
    geometry = wkt.loads(wkt_string)

    # Convert Shapely geometry to GeoJSON format
    # geojson_geometry = shapely.geometry.mapping(reverse(geometry))
    geojson_geometry = shapely.geometry.mapping(geometry)

    return geojson_geometry

features = []
csv = pd.read_csv(f'{FILE_NAME}.csv')
for i, row in csv.iterrows():
    shapelyObject = wkt_to_geojson(row['geometry'])
    # features.append(json.dumps({ 'type': 'Feature', 'properties': { 'id': row['id'], 'name': row['service_area'] }, 'geometry': shapelyObject }))
    # features.append(json.dumps({ 'type': 'Feature', 'properties': { 'id': str(row['id']), 'service_area': row['service_area'] }, 'geometry': shapelyObject }))
    features.append(json.dumps({ 'type': 'Feature', 'properties': { 'id': str(row['id']), 'zipcode': str(row['zipcode']), 'service_area': row['service_area'] }, 'geometry': shapelyObject }))

# print(features)

with open(f'{FILE_NAME}.geojson', 'w') as f:
    f.write('{\n\
"type": "FeatureCollection",\n\
"features": [\n')

    num_commas = len(features) - 1
    for i, feature in enumerate(features):
        f.write(feature)
        if i < num_commas:
            f.write(',')
        f.write('\n')

    f.write(']\n}\n')
