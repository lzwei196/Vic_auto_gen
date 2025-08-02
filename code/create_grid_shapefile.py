# 脚本名称: create_grid_shapefile.py
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path

SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\soil_param_with_resid.txt")
GRID_SHP_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\source_data\soil\master_grid_649.shp")

print(f"正在读取: {SOIL_PARAM_IN.name}")
df = pd.read_csv(SOIL_PARAM_IN, sep=' ', header=None, dtype=str)
df.columns = [f'col_{i+1}' for i in range(df.shape[1])]

geometry = [Point(xy) for xy in zip(df['col_4'].astype(float), df['col_3'].astype(float))]
gdf = gpd.GeoDataFrame(df[['col_2']], geometry=geometry, crs="EPSG:4326")
gdf.rename(columns={'col_2': 'grid_id'}, inplace=True)

gdf.to_file(GRID_SHP_OUT)
print(f"成功创建格网点Shapefile文件: {GRID_SHP_OUT}")