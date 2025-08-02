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
from rasterio.enums import Resampling

# --- 0. 忽略良性的库警告 ---
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="The 'band' dimension is ignored by rasterio")

# --- 1. 配置核心输入路径 ---
MASTER_GRID_NC = Path(r"H:\CMFD\huai\Data_forcing_01dy_010deg\wind_CMFD_V0200_B-01_01dy_025deg_202001-202012_huai.nc")
ELEV_NC_IN = Path(r"H:\CMFD\Data_ancillary\elev_CMFD_V0200_B-00_fx_010deg.nc")
VEG_RASTER_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\source_data\veg\AVHRR_1km_LANDCOVER_1981_1994.GLOBAL.tif")
VEGLIB_FILE = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\veg_lib_IGBP")

# --- 2. 配置输出路径 ---
OUTPUT_DIR = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param")
SOIL_PARAM_OUT = OUTPUT_DIR / "soil_param_final.txt"
VEG_PARAM_OUT = OUTPUT_DIR / "veg_param_final.txt"

# --- 3. 准备工作 ---
os.makedirs(OUTPUT_DIR, exist_ok=True)
print("最终一体化脚本处理开始...")

# --- 4. 定义最终的“主格网” ---
print(f"正在从 {MASTER_GRID_NC.name} 定义主格网...")
with xr.open_dataset(MASTER_GRID_NC) as ds_master:
    # ====================================================================
    # --- 关键修正 ---
    # 明确为“主格网”模板文件指定坐标系，以解决 Missing dst_crs 错误
    ds_master = ds_master.rio.write_crs("EPSG:4326")
    # ====================================================================
    
    master_var = list(ds_master.data_vars)[0]
    valid_points = ds_master[master_var].stack(gridcell=('y', 'x')).dropna('gridcell')
    lats = valid_points.coords['y'].values
    lons = valid_points.coords['x'].values
    num_final_cells = len(lats)
print(f"主格网已确定！有效单元格数量为: {num_final_cells}。")


# --- 5. 生成并填充土壤参数文件 ---
print("\n--- 正在生成并填充土壤参数文件 ---")
# 5.1 创建土壤参数文件框架
df_soil = pd.DataFrame(np.full((num_final_cells, 53), -9999.0))
df_soil.columns = [f'col_{i}' for i in range(df_soil.shape[1])]
# 5.2 填充基础信息
df_soil.iloc[:, 0] = 1
df_soil.iloc[:, 1] = np.arange(1, num_final_cells + 1)
df_soil.iloc[:, 2] = lats
df_soil.iloc[:, 3] = lons

# 5.3 使用区域平均重采样填充高程值
print("正在使用区域平均重采样方法计算高程值...")
with xr.open_dataset(ELEV_NC_IN) as ds_elev_raw, xr.open_dataset(MASTER_GRID_NC) as ds_template:
    # 再次为模板指定CRS
    ds_template = ds_template.rio.write_crs("EPSG:4326")
    
    elev_var = list(ds_elev_raw.data_vars)[0]
    ds_elev_raw = ds_elev_raw.rio.write_crs("EPSG:4326")
    
    reprojected_elev = ds_elev_raw[elev_var].rio.reproject_match(ds_template, resampling=Resampling.average)
    
    lats_to_find = xr.DataArray(lats, dims="points")
    lons_to_find = xr.DataArray(lons, dims="points")
    elev_values = reprojected_elev.sel(y=lats_to_find, x=lons_to_find, method='nearest')
    elev_values_filled = elev_values.fillna(0.0)
    
    df_soil.iloc[:, 21] = elev_values_filled.values
print("高程值填充完毕！")

# 5.4 按精确格式写入土壤参数文件
print(f"正在写入最终土壤参数文件: {SOIL_PARAM_OUT.name}")
df_soil_to_write = df_soil.astype(object)
with open(SOIL_PARAM_OUT, 'w') as f:
    for index, row in df_soil_to_write.iterrows():
        formatted_items = []
        for i, item in enumerate(row):
            if i in [0, 1]: formatted_items.append(str(int(item)))
            elif i in [2, 3]: formatted_items.append(f"{float(item):.4f}")
            elif i == 21: formatted_items.append(f"{float(item):.2f}")
            else:
                if pd.isna(item) or item == -9999.0: formatted_items.append('-9999')
                elif item == int(item): formatted_items.append(str(int(item)))
                else: formatted_items.append(f"{float(item):.3f}")
        f.write(" ".join(formatted_items) + "\n")
print("土壤参数文件生成成功！")


# --- 6. 生成植被参数文件 ---
print("\n--- 正在生成植被参数文件 ---")
# 6.1 解析植被库
try:
    lai_lookup = {}; root_zone_lookup = {}
    with open(VEGLIB_FILE, 'r') as f:
        for line in f:
            if line.strip().startswith('#') or not line.strip(): continue
            parts = line.split(); veg_class = int(parts[0])
            lai_values = [f"{float(v):.3f}" for v in parts[4:16]]; lai_lookup[veg_class] = lai_values
except FileNotFoundError: print(f"错误: 找不到植被库文件 {VEGLIB_FILE}。"); exit()
root_zone_lookup = {
    0: ['0.1', '0.6', '0.8', '0.44', '0.45', '0.11'], 1: ['0.1', '0.6', '1.1', '0.34', '0.51', '0.14'],
    2: ['0.1', '0.6', '2.3', '0.32', '0.44', '0.23'], 3: ['0.1', '0.6', '1.3', '0.34', '0.5', '0.16'],
    4: ['0.1', '0.6', '1.3', '0.31', '0.52', '0.17'], 5: ['0.1', '0.6', '1.7', '0.25', '0.52', '0.22'],
    6: ['0.1', '0.6', '1.8', '0.31', '0.49', '0.21'], 7: ['0.1', '0.6', '2.4', '0.33', '0.43', '0.24'],
    8: ['0.1', '0.6', '1.7', '0.36', '0.45', '0.19'], 9: ['0.1', '0.6', '1.0', '0.37', '0.5', '0.13'],
    10: ['0.1', '0.6', '0.8', '0.44', '0.45', '0.11'], 11: ['0.1', '0.6', '0.8', '0.44', '0.45', '0.11'],
    12: ['0.1', '0.6', '0.8', '0.33', '0.55', '0.12'], 13: ['0.1', '0.6', '0.8', '0.44', '0.45', '0.11'],
    14: ['0.1', '0.6', '0.8', '0.33', '0.55', '0.12'], 15: ['0.1', '0.6', '0.8', '0.44', '0.45', '0.11'],
    16: ['0.1', '0.6', '3.3', '0.22', '0.46', '0.31'], 'default': ['0.1', '0.6', '1.0', '0.4', '0.4', '0.2']
}

# 6.2 创建地理边界并进行空间统计
resolution = abs(ds_master['y'].values[1] - ds_master['y'].values[0])
polygons = [box(lon - resolution / 2, lat - resolution / 2, lon + resolution / 2, lat + resolution / 2) for lat, lon in zip(lats, lons)]
grid_gdf = gpd.GeoDataFrame(geometry=polygons, crs="EPSG:4326")
try:
    with rioxarray.open_rasterio(VEG_RASTER_IN) as rds:
        if str(rds.rio.crs) != str(grid_gdf.crs): grid_gdf = grid_gdf.to_crs(rds.rio.crs)
except Exception as e: print(f"错误: 读取植被栅格时出错。 {e}"); exit()
print("正在为最终有效格网进行空间统计...")
stats = zonal_stats(grid_gdf, str(VEG_RASTER_IN), categorical=True, geojson_out=True)
print("空间统计完成。")

# 6.3 整理并写入植被文件
stats_gdf = gpd.GeoDataFrame.from_features(stats)
output_lines = []
for index, row in stats_gdf.iterrows():
    cell_id = index + 1
    properties = {k: v for k, v in row.items() if isinstance(k, int) and pd.notna(v)}
    if 16 in properties: del properties[16]
    total_pixels = sum(properties.values())
    if total_pixels == 0: continue
    
    veg_fractions = {code: count / total_pixels for code, count in properties.items()}
    filtered_veg = {code: frac for code, frac in veg_fractions.items() if frac >= 0.03}
    if not filtered_veg: continue
        
    final_total_fraction = sum(filtered_veg.values())
    final_veg_info = {code: frac / final_total_fraction for code, frac in filtered_veg.items()}
    
    line_block = [f"{cell_id}\t{len(final_veg_info)}"]
    for veg_class, fraction in final_veg_info.items():
        root_params = root_zone_lookup.get(veg_class, root_zone_lookup['default'])
        lai_params = lai_lookup.get(veg_class, [])
        line_block.append(f"\t \t{veg_class}\t{fraction:.2f}\t{' '.join(root_params)}")
        lai_string = "\t".join(lai_params); line_block.append(f"  \t \t {lai_string}")
    
    if len(line_block) > 1: output_lines.append("\n".join(line_block))

# 6.4 写入文件
if output_lines:
    with open(VEG_PARAM_OUT, 'w') as f: f.write("\n".join(output_lines) + "\n")
    print(f"植被参数文件生成成功！共为 {len(output_lines)} 个格网生成了参数。")
else:
    print("未能生成任何有效的植被参数。")

print("\n全部处理成功完成！")