import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path
import os
import geopandas as gpd
from shapely.geometry import box
from rasterstats import zonal_stats
import warnings
import rioxarray

# --- 0. 忽略良性的库警告 ---
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="The 'band' dimension is ignored by rasterio")

# --- 1. 配置路径 ---
MASTER_GRID_NC = Path(r"H:\CMFD\huai\Data_forcing_01dy_025deg\wind_CMFD_V0200_B-01_01dy_025deg_202001-202012_huai.nc")
VEG_RASTER_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\source_data\veg\AVHRR_1km_LANDCOVER_1981_1994.GLOBAL.tif")
VEGLIB_FILE = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\veglib.LDAS")
VEG_PARAM_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\vic_veg_param_final.txt")

# --- 2. 准备工作 ---
os.makedirs(VEG_PARAM_OUT.parent, exist_ok=True)
print("处理开始...")

# --- 3. 解析植被库文件 ---
print(f"正在解析植被库文件: {VEGLIB_FILE.name}")
try:
    lai_lookup = {}
    with open(VEGLIB_FILE, 'r') as f:
        for line in f:
            if line.strip().startswith('#') or not line.strip(): continue
            parts = line.split()
            veg_class = int(parts[0])
            lai_values = [f"{float(v):.3f}" for v in parts[4:16]]
            lai_lookup[veg_class] = lai_values
except FileNotFoundError:
    print(f"错误: 找不到植被库文件 {VEGLIB_FILE}。请检查路径。"); exit()

root_zone_lookup = {
    0: ['0.1', '0.44', '0.6', '0.45', '0.8', '0.11'], 1: ['0.10', '0.34', '0.6', '0.52', '0.8', '0.14'],
    2: ['0.1', '0.32', '0.6', '0.44', '2.3', '0.23'], 3: ['0.1', '0.34', '0.6', '0.5', '1.3', '0.16'],
    4: ['0.10', '0.31', '0.6', '0.52', '1.3', '0.17'], 5: ['0.10', '0.25', '0.60', '0.52', '1.70', '0.22'],
    6: ['0.10', '0.30', '0.60', '0.5', '2.00', '0.2'], 7: ['0.10', '0.37', '0.60', '0.5', '0.10', '0.3'],
    8: ['0.10', '0.31', '0.60', '0.48', '1.80', '0.21'], 9: ['0.10', '0.33', '0.60', '0.43', '2.40', '0.24'],
    10: ['0.10', '0.36', '0.60', '0.45', '1.70', '0.19'], 11: ['0.10', '0.33', '0.6', '0.55', '0.80', '0.12'],
    12: ['0.1', '0.22', '0.6', '0.46', '3.3', '0.31'], 14: ['0.1', '0.44', '0.6', '0.45', '0.8', '0.11'], 
	'default': ['0.10', '0.10', '1.00', '0.70', '0.50', '0.20']
}
print("植被库和根系参数查找表创建完成。")

# --- 4. 创建主格网的地理边界 ---
print(f"正在从 {MASTER_GRID_NC.name} 创建主格网...")
with xr.open_dataset(MASTER_GRID_NC) as ds_template:
    data_var_name = list(ds_template.data_vars)[0]
    valid_points = ds_template[data_var_name].stack(gridcell=('y', 'x')).dropna('gridcell')
    lats = valid_points.coords['y'].values
    lons = valid_points.coords['x'].values
    resolution = abs(ds_template['y'].values[1] - ds_template['y'].values[0])
    polygons = [box(lon - resolution / 2, lat - resolution / 2, lon + resolution / 2, lat + resolution / 2) for lat, lon in zip(lats, lons)]
    grid_gdf = gpd.GeoDataFrame(geometry=polygons, crs="EPSG:4326")
    grid_gdf['lat'] = lats
    grid_gdf['lon'] = lons
print(f"主格网有效单元格数量为: {len(grid_gdf)}。")

# --- 5. 执行空间统计 ---
try:
    with rioxarray.open_rasterio(VEG_RASTER_IN) as rds:
        if str(rds.rio.crs) != str(grid_gdf.crs):
            grid_gdf = grid_gdf.to_crs(rds.rio.crs)
except Exception as e:
    print(f"错误: 读取植被栅格时出错。 {e}"); exit()

print("正在对高分辨率植被图进行空间统计 (这可能需要一些时间)...")
# ====================================================================
# --- 关键修正: 移除 nodata=0，让水体(ID=0)参与统计 ---
stats = zonal_stats(grid_gdf, str(VEG_RASTER_IN), categorical=True, geojson_out=True)
# ====================================================================
print("空间统计完成。")

# --- 6. 整理统计结果并生成最终文件 ---
print(f"正在生成VIC植被参数文件: {VEG_PARAM_OUT.name}\n")
stats_gdf = gpd.GeoDataFrame.from_features(stats)
stats_gdf = stats_gdf.sort_values(by=['lat', 'lon'], ascending=[False, True]).reset_index(drop=True)

output_lines = []
for index, row in stats_gdf.iterrows():
    cell_id = index + 1
    properties = {k: v for k, v in row.items() if isinstance(k, int) and pd.notna(v)}
    
    # 剔除裸地(ID 16)
    if 16 in properties:
        del properties[16]
    
    total_pixels = sum(properties.values())
    if total_pixels == 0:
        continue # 如果剔除裸地后没有其他类型了，则跳过
    
    veg_fractions = {veg_code: count / total_pixels for veg_code, count in properties.items()}
    filtered_veg = {code: frac for code, frac in veg_fractions.items() if frac >= 0.03}
    
    if not filtered_veg:
        continue
        
    final_total_fraction = sum(filtered_veg.values())
    final_veg_info = {code: frac / final_total_fraction for code, frac in filtered_veg.items()}
    
    line_block = []
    line_block.append(f"{cell_id}\t{len(final_veg_info)}")
    for veg_class, fraction in final_veg_info.items():
        root_params = root_zone_lookup.get(veg_class, root_zone_lookup['default'])
        lai_params = lai_lookup.get(veg_class)
        if lai_params is None:
            continue
        line_block.append(f"\t \t{veg_class}\t{fraction:.2f}\t{' '.join(root_params)}")
        lai_string = "\t".join(lai_params)
        line_block.append(f"  \t \t {lai_string}")
    
    if len(line_block) > 1:
        output_lines.append("\n".join(line_block))

# --- 7. 写入文件 ---
if output_lines:
    with open(VEG_PARAM_OUT, 'w') as f:
        f.write("\n".join(output_lines))
        f.write("\n")
    print(f"\n处理成功完成！共为 {len(output_lines)} 个有效格网生成了参数。")
else:
    print("\n处理完成，但未能生成任何有效的植被参数。输出文件为空。")