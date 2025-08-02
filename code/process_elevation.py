import xarray as xr
import geopandas as gpd
import rioxarray
from pathlib import Path
import os
from rasterio.enums import Resampling

# --- 1. 配置路径 (已根据您的信息设置，无需修改) ---

# 输入的全国高程NC文件
ELEV_NC_IN = Path(r"H:\CMFD\Data_ancillary\elev_CMFD_V0200_B-00_fx_010deg.nc")

# 用于裁剪的淮河流域Shapefile
SHP_FILE = Path(r"C:\Users\yc\Desktop\vic\huaihe\vic_result\grid\huaihe.shp")

# 输出路径和文件名
OUTPUT_DIR = Path(r"H:\CMFD\huai\Data_ancillary")
OUTPUT_FILENAME = "elev_CMFD_V0200_B-00_fx_025deg_huai.nc"
ELEV_NC_OUT = OUTPUT_DIR / OUTPUT_FILENAME

# --- 2. 准备工作 ---
os.makedirs(OUTPUT_DIR, exist_ok=True)
print("处理开始...")
print(f"输入文件: {ELEV_NC_IN}")
print(f"Shapefile: {SHP_FILE}")

# --- 3. 读取并准备数据 ---
# 读取Shapefile
try:
    huai_basin_gdf = gpd.read_file(SHP_FILE)
    if not huai_basin_gdf.crs or huai_basin_gdf.crs.to_epsg() != 4326:
        huai_basin_gdf = huai_basin_gdf.to_crs("EPSG:4326")
    print("Shapefile 读取成功 (WGS84)。")
except Exception as e:
    print(f"错误: 无法读取Shapefile. {e}")
    exit()

# 读取高程NetCDF文件
try:
    elev_ds = xr.open_dataset(ELEV_NC_IN)
    # 明确数据坐标系为 WGS84
    elev_ds = elev_ds.rio.write_crs("EPSG:4326")
    print("高程NC文件读取成功。")
except Exception as e:
    print(f"错误: 无法读取高程NC文件. {e}")
    exit()

# --- 4. 核心处理流程 ---
try:
    # 步骤 1: 裁剪到淮河流域
    print("正在裁剪高程数据...")
    clipped_elev = elev_ds.rio.clip(huai_basin_gdf.geometry, drop=True)

    # 步骤 2: 重采样到0.25度
    print("正在重采样至 0.25° 分辨率...")
    # 对于高程数据，使用双线性插值(bilinear)或平均(average)都可以
    resampled_elev = clipped_elev.rio.reproject(
        dst_crs=clipped_elev.rio.crs,
        resolution=0.25,
        resampling=Resampling.bilinear 
    )

    # 步骤 3 (可选，但推荐): 移除 rioxarray 添加的 spatial_ref 变量，保持文件干净
    print("正在清理 'spatial_ref' 变量...")
    if "spatial_ref" in resampled_elev.coords:
        resampled_elev = resampled_elev.drop_vars("spatial_ref")
    for var in resampled_elev.data_vars:
        if 'grid_mapping' in resampled_elev[var].attrs:
            del resampled_elev[var].attrs['grid_mapping']

    # --- 5. 保存输出文件 ---
    print(f"正在保存至: {ELEV_NC_OUT}")
    resampled_elev.to_netcdf(ELEV_NC_OUT)
    
    print("\n处理成功完成！")

except Exception as e:
    print(f"\n处理过程中发生错误: {e}")

finally:
    # 关闭数据集
    if 'elev_ds' in locals():
        elev_ds.close()