import pandas as pd
from shapely import wkt
from shapely.ops import transform
import pyproj

# Function to convert WKT to latlon
def convert_wkt_to_latlon(wkt_geometry):
    # Define projection transformer
    transformer = pyproj.Transformer.from_crs("epsg:28992", "epsg:4326", always_xy=True)

    # Parse WKT and transform coordinates
    geometry = wkt.loads(wkt_geometry)
    latlon_geometry = transform(transformer.transform, geometry)

    return latlon_geometry

# Read CSV file into a DataFrame
file_path = 'service_areas.csv'  # Replace with the actual path to your CSV file
df = pd.read_csv(file_path)

# Convert 'geomtext' column to latlon format
df['geomtext_latlon'] = df['geomtext'].apply(convert_wkt_to_latlon)

# Save the updated DataFrame to a new CSV file
output_file_path = 'service_areas_latlon.csv'  # Replace with the desired output file path
df.to_csv(output_file_path, index=False)

print(f"Conversion complete. Results saved to {output_file_path}")


# # Read CSV file into a DataFrame
# file_path = 'service_areas_latlon.csv'  # Replace with the actual path to your CSV file
# df = pd.read_csv(file_path)

# # Convert 'geomtext' column to latlon format
# df.drop(columns=['geom', 'geomtext'], inplace=True)

# # Save the updated DataFrame to a new CSV file
# output_file_path = 'service_areas.csv'  # Replace with the desired output file path
# df.to_csv(output_file_path, index=False)
