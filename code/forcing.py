import xarray as xr
import geopandas as gpd
import rioxarray
from pathlib import Path
import os
import warnings
from rasterio.enums import Resampling
import re

# ====================================================================
# --- 0. 配置 ---
# ====================================================================
# 在这里填入所有需要处理的变量名缩写
VARIABLES_TO_PROCESS = [
    "wind", "temp", "pres", "shum", "rhum", "srad", "lrad", "prec"
]
# 设置年份范围
YEAR_START = 1991
YEAR_END = 2020

# --- 1. 文件路径 (固定，无需修改) ---
INPUT_DATA_DIR = Path(r"H:\CMFD\Data_forcing_01dy_010deg")
SHP_FILE_PATH = Path(r"C:\Users\yc\Desktop\vic\huaihe\vic_result\grid\huaihe.shp")
OUTPUT_DIR = Path(r"H:\CMFD\huai\Data_forcing_01dy_010deg")

# --- 2. 初始化和检查 ---
warnings.simplefilter(action='ignore', category=FutureWarning)
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"输入路径: {INPUT_DATA_DIR}")
print(f"Shapefile路径: {SHP_FILE_PATH}")
print(f"输出路径: {OUTPUT_DIR}\n")

# --- 3. 读取并准备淮河流域的 shapefile ---
print(f"--- 步骤1: 读取 Shapefile ---")
try:
    huai_basin_gdf = gpd.read_file(SHP_FILE_PATH)
    if not huai_basin_gdf.crs or huai_basin_gdf.crs.to_epsg() != 4326:
        huai_basin_gdf = huai_basin_gdf.to_crs("EPSG:4326")
    print("Shapefile 已准备就绪 (WGS84 坐标系)。")
except Exception as e:
    print(f"错误：无法读取 Shapefile 文件。 {e}")
    exit()

# ====================================================================
# --- 4. 批量处理所有指定的变量 ---
# ====================================================================
for var_name in VARIABLES_TO_PROCESS:
    print(f"\n{'='*25} 开始处理变量: {var_name.upper()} {'='*25}")
    
    # 步骤 4a: 查找所有匹配变量名的文件
    all_nc_files = list(INPUT_DATA_DIR.glob(f"{var_name}_*.nc"))

    # ====================================================================
    # --- 新增步骤 4b: 根据年份筛选文件 (1990-2020) ---
    # ====================================================================
    print(f"从 {len(all_nc_files)} 个文件中筛选 {YEAR_START}-{YEAR_END} 年的数据...")
    filtered_files = []
    for nc_file in all_nc_files:
        try:
            # 从文件名的最后一部分提取年份
            date_part = nc_file.stem.split('_')[-1]
            year = int(date_part[:4])
            # 检查年份是否在指定范围内
            if YEAR_START <= year <= YEAR_END:
                filtered_files.append(nc_file)
        except (IndexError, ValueError):
            print(f"  - 警告: 文件名 '{nc_file.name}' 格式不规范, 无法提取年份, 已跳过。")
    
    # 后续的处理将使用筛选后的 `filtered_files` 列表
    nc_files = filtered_files
    
    if not nc_files:
        print(f"警告：在 {YEAR_START}-{YEAR_END} 年范围内未找到变量 '{var_name}' 的任何文件，跳过...")
        continue

    print(f"筛选完毕, 共有 {len(nc_files)} 个 {var_name.upper()} 文件待处理。")
    
    # 步骤 4c: 循环处理筛选后的文件
    for nc_file in nc_files:
        try:
            print(f"\n>>> 正在处理: {nc_file.name}")
            
            with xr.open_dataset(nc_file) as xds:
                xds = xds.rio.write_crs("EPSG:4326", inplace=True)
                
                print("   - 正在进行裁剪操作...")
                clipped_ds = xds.rio.clip(huai_basin_gdf.geometry.values, huai_basin_gdf.crs, drop=True, all_touched=True)

                print("   - 正在重采样至 0.25° 分辨率...")
                resampled_ds = clipped_ds.rio.reproject(
                    dst_crs=clipped_ds.rio.crs, resolution=0.25, resampling=Resampling.average
                )

                print("   - 正在移除 'spatial_ref' 变量...")
                if "spatial_ref" in resampled_ds.coords:
                    resampled_ds = resampled_ds.drop_vars("spatial_ref")
                
                for var in resampled_ds.data_vars:
                    if 'grid_mapping' in resampled_ds[var].attrs:
                        del resampled_ds[var].attrs['grid_mapping']

                base_name = re.sub(r'_\d{3}deg_', '_025deg_', nc_file.stem)
                output_filename = f"{base_name}_huai.nc"
                output_path = OUTPUT_DIR / output_filename
                
                encoding = {var: {'_FillValue': xds[var].attrs.get('_FillValue', -9999)} for var in resampled_ds.data_vars}
                resampled_ds.to_netcdf(output_path, encoding=encoding)
                
                print(f"   - 处理完成，已保存至: {output_path}")

        except Exception as e:
            print(f"   - 处理文件 {nc_file.name} 时发生错误: {e}")
            continue

print(f"\n{'='*20} 所有指定变量处理完毕! {'='*20}")