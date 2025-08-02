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

# --- 1. 配置核心输入路径 ---
MASTER_GRID_NC = Path(r"H:\CMFD\huai\Data_forcing_01dy_010deg\wind_CMFD_V0200_B-01_01dy_025deg_202001-202012_huai.nc")
ELEV_NC_IN = Path(r"H:\CMFD\Data_ancillary\elev_CMFD_V0200_B-00_fx_010deg.nc")
MET_DATA_DIR = Path(r"H:\CMFD\huai\Data_forcing_01dy_010deg")
SOIL_RASTER_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\source_data\soil\HWSD_China_Geo.img")
VEGLIB_FILE = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\veg_lib_IGBP.txt")

# --- 2. 配置输出路径 ---
OUTPUT_DIR = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param")
SOIL_PARAM_OUT = OUTPUT_DIR / "SOIL_PARAM_FINAL.txt"
VEG_PARAM_OUT = OUTPUT_DIR / "VEG_PARAM_FINAL.txt"

# --- 3. 准备工作 ---
os.makedirs(OUTPUT_DIR, exist_ok=True)
print("最终土壤参数一体化生成脚本开始...")

# --- 4. 定义主格网 ---
print(f"正在从 {MASTER_GRID_NC.name} 定义主格网...")
with xr.open_dataset(MASTER_GRID_NC) as ds_master:
    master_var = list(ds_master.data_vars)[0]
    valid_points = ds_master[master_var].stack(gridcell=('y', 'x')).dropna('gridcell')
    lats = valid_points.coords['y'].values
    lons = valid_points.coords['x'].values
    num_final_cells = len(lats)
print(f"主格网已确定！有效单元格数量为: {num_final_cells}。")

# --- 5. 生成并填充土壤参数文件 ---
print("\n--- 正在构建并填充土壤参数文件 ---")
df_soil = pd.DataFrame(index=range(num_final_cells), columns=[f'col_{i+1}' for i in range(53)], dtype=object)
df_soil.iloc[:, 0] = 1
df_soil.iloc[:, 1] = np.arange(1, num_final_cells + 1)
df_soil.iloc[:, 2] = lats
df_soil.iloc[:, 3] = lons
print("基础信息填充完毕。")

# 5.1 【核心修正】使用最稳健的逐点循环法填充高程
print("正在使用逐点查找法填充高程值...")
with xr.open_dataset(ELEV_NC_IN) as ds_elev_raw:
    elev_var = list(ds_elev_raw.data_vars)[0]
    elev_values = []
    for i in range(num_final_cells):
        lat, lon = lats[i], lons[i]
        try:
            # 在原始0.1度高程数据中查找最近点的值
            val = ds_elev_raw[elev_var].sel(lat=lat, lon=lon, method='nearest').item()
            # 如果值为NaN（代表海洋），则设为0.0
            if pd.isna(val):
                elev_values.append(0.0)
            else:
                elev_values.append(val)
        except Exception:
            # 如果发生任何其他错误，也设为0.0
            elev_values.append(0.0)
    df_soil['col_22'] = elev_values
print("高程值填充完毕！")

# 5.2 填充年平均降水
print("正在填充年平均降水...")
try:
    with xr.open_mfdataset(str(MET_DATA_DIR / "prec_*_huai.nc"), chunks='auto') as ds_prec:
        prec_var = list(ds_prec.data_vars)[0]
        mean_prec_rate_mm_per_sec = ds_prec[prec_var].mean(dim='time').compute()
        annual_prec = (mean_prec_rate_mm_per_sec * 86400) * 365.25
        lats_to_find = xr.DataArray(lats, dims="points"); lons_to_find = xr.DataArray(lons, dims="points")
        prec_values = annual_prec.sel(y=lats_to_find, x=lons_to_find, method="nearest").fillna(0.0)
        df_soil['col_49'] = prec_values.values
except Exception:
    print("警告：未能成功计算年平均降水，将使用-9999填充。")
    df_soil['col_49'] = -9999.0
print("年平均降水填充完毕。")

# 5.3 获取主导土壤类型
print("\n--- 正在从HWSD栅格中提取主导土壤类型 ---")
grid_gdf = gpd.GeoDataFrame(geometry=[box(lon - 0.125, lat - 0.125, lon + 0.125, lat + 0.125) for lat, lon in zip(lats, lons)], crs="EPSG:4326")
try:
    with rioxarray.open_rasterio(SOIL_RASTER_IN) as rds:
        if str(rds.rio.crs) != str(grid_gdf.crs): grid_gdf = grid_gdf.to_crs(rds.rio.crs)
    stats_t = zonal_stats(grid_gdf, str(SOIL_RASTER_IN), band=1, stats="majority")
    soil_code_t = [s['majority'] if s['majority'] is not None else 1 for s in stats_t]
    stats_s = zonal_stats(grid_gdf, str(SOIL_RASTER_IN), band=2, stats="majority")
    soil_code_s = [s['majority'] if s['majority'] is not None else 1 for s in stats_s]
except Exception as e:
    print(f"错误: 空间统计失败，将使用默认土壤类型ID '1'。错误: {e}")
    soil_code_t = [1] * num_final_cells
    soil_code_s = [1] * num_final_cells
print("主导土壤类型提取完毕。")

# 5.4 根据R代码逻辑填充剩余参数
print("\n--- 正在根据R代码逻辑填充所有剩余参数 ---")
mdata = {1:[1,0,0,0,0,0], 2:[2,708,0.37,0.25,21.868,1400], 3:[3,763.2,0.36,0.17,27.691,1260], 4:[4,1096.8,0.36,0.21,15.195,0],
         5:[5,424.8,0.34,0.21,16.888,1350], 6:[6,2061.6,0.28,0.08,8.509,0], 7:[7,950.4,0.32,0.12,11.064,1380], 8:[8,285.6,0.31,0.23,12.302,0],
         9:[9,472.8,0.29,0.14,13.362,1410], 10:[10,576,0.27,0.17,18.152,1410], 11:[11,1257.6,0.21,0.09,12.524,1480],
         12:[12,2608.8,0.15,0.06,11.888,1660], 13:[13,9218.4,0.08,0.03,11.734,1740]}

df_soil[['col_5', 'col_6', 'col_7', 'col_8', 'col_9']] = [0.3, 0.02, 10.00, 0.7, 2]
df_soil[['col_47', 'col_48']] = [0.01, 0.03]
df_soil[['col_16','col_17','col_18','col_19','col_20','col_24','col_25','col_28','col_29','col_30','col_31','col_32','col_33','col_54']] = -9999.0
df_soil[['col_23', 'col_27', 'col_37', 'col_38', 'col_39', 'col_50', 'col_51', 'col_52', 'col_53']] = [0.1, 4.0, 2685, 2685, 2685, 0, 0, 0, 0]
df_soil['col_10'] = [mdata.get(tid, mdata[1])[4] for tid in soil_code_t]; df_soil['col_11'] = df_soil['col_10']; df_soil['col_12'] = [mdata.get(tid, mdata[1])[4] for tid in soil_code_s]
df_soil['col_13'] = [mdata.get(tid, mdata[1])[1] for tid in soil_code_t]; df_soil['col_14'] = df_soil['col_13']; df_soil['col_15'] = [mdata.get(tid, mdata[1])[1] for tid in soil_code_s]
df_soil['col_34'] = [mdata.get(tid, mdata[1])[5] for tid in soil_code_t]; df_soil['col_35'] = df_soil['col_34']; df_soil['col_36'] = [mdata.get(tid, mdata[1])[5] for tid in soil_code_s]
df_soil['col_41'] = [mdata.get(tid, mdata[1])[2] for tid in soil_code_t]; df_soil['col_42'] = df_soil['col_41']; df_soil['col_43'] = [mdata.get(tid, mdata[1])[2] for tid in soil_code_s]
df_soil['col_44'] = [mdata.get(tid, mdata[1])[3] for tid in soil_code_t]; df_soil['col_45'] = df_soil['col_44']; df_soil['col_46'] = [mdata.get(tid, mdata[1])[3] for tid in soil_code_s]
df_soil['col_40'] = (df_soil['col_4'].astype(float) * 24 / 360).round(1)
print("所有参数填充完毕。")

# 5.5 按精确格式保存最终文件
print(f"\n正在写入最终土壤参数文件: {SOIL_PARAM_OUT.name}")
with open(SOIL_PARAM_OUT, 'w') as f:
    for index, row in df_soil.iterrows():
        formatted_items = []
        for i, item in enumerate(row):
            col_index = i + 1
            if col_index in [1, 2, 37, 38, 39, 53]: formatted_items.append(str(int(item)))
            elif col_index in [3, 4]: formatted_items.append(f"{float(item):.4f}")
            elif col_index == 22: formatted_items.append(f"{float(item):.2f}")
            else:
                num = float(item)
                if num == -9999.0: formatted_items.append('-9999')
                else: formatted_items.append(f"{num:.3f}")
        f.write(" ".join(formatted_items) + "\n")
print("土壤参数文件生成成功！")

# ... (植被文件生成部分省略，与上一版相同) ...
print("\n全部处理成功完成！")