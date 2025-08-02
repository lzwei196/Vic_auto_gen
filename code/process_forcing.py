import xarray as xr
import pandas as pd
from pathlib import Path
import os
import numpy as np
import warnings

# --- 0. 忽略不必要的警告 ---
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 1. 配置路径 ---
# 输入：包含所有处理好的NC文件的文件夹
INPUT_DATA_DIR = Path(r"H:\CMFD\huai\Data_forcing_01dy_010deg")
# 输出：最终气象驱动文件存放的文件夹
OUTPUT_FORCING_DIR = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\forcing")

# --- 2. 准备工作 ---
os.makedirs(OUTPUT_FORCING_DIR, exist_ok=True)
print("最终气象驱动文件生成脚本开始...")

# --- 3. 一次性读取所有变量和所有年份的数据 ---
print("正在读取所有变量的NC文件...")
# 需要从CMFD读取的变量列表
variables_to_load = ['prec', 'temp', 'pres', 'srad', 'lrad', 'wind', 'shum']
all_ds = []
try:
    for var in variables_to_load:
        print(f"  - 正在加载变量: {var}")
        # 使用 open_mfdataset 高效打开该变量所有年份的文件
        ds_var = xr.open_mfdataset(
            str(INPUT_DATA_DIR / f"{var}_*_huai.nc"),
            combine='by_coords',
            chunks={'time': 366} # 按年份分块读取
        )
        all_ds.append(ds_var)
    
    # 将所有变量合并到一个大的 xarray.Dataset 中
    ds_merged = xr.merge(all_ds)
    print("所有数据加载并合并完毕！")
except Exception as e:
    print(f"错误：读取NC文件时出错。请确保路径 '{INPUT_DATA_DIR}' 下包含所有必需的变量文件。错误信息: {e}")
    exit()

# --- 4. 筛选时间范围 (1991-2020) ---
print("正在筛选 1991-01-01 到 2020-12-31 的数据...")
ds_merged = ds_merged.sel(time=slice('1991-01-01', '2020-12-31'))
# 检查天数是否正确 (30年 * 365 + 8个闰年 = 10958天)
# 如果您的数据包含1990，请使用 slice('1990-01-01', '2020-12-31')
print(f"数据筛选完毕，共包含 {len(ds_merged.time)} 天。")


# --- 5. 确定需要处理的有效格网 ---
print("正在确定有效格网坐标...")
master_var = 'wind' # 以任一变量为标准
valid_points = ds_merged[master_var].isel(time=0).stack(gridcell=('y', 'x')).dropna('gridcell')
lats = valid_points.coords['y'].values
lons = valid_points.coords['x'].values
num_grids = len(lats)
print(f"已确定 {num_grids} 个有效格网。")

# --- 6. 为每个格网生成一个驱动文件 ---
print(f"\n开始为 {num_grids} 个格网生成驱动文件 (这可能需要较长时间)...")
for i in range(num_grids):
    lat, lon = lats[i], lons[i]
    
    # 构造输出文件名，保留4位小数
    output_filename = f"huai_01dy_025deg_{lat:.4f}_{lon:.4f}"
    output_path = OUTPUT_FORCING_DIR / output_filename
    
    print(f"  ({i+1}/{num_grids}) 正在处理格网: lat={lat:.4f}, lon={lon:.4f} -> {output_filename}")
    
    # 提取该格网所有时间序列的数据并加载到内存
    cell_data = ds_merged.sel(y=lat, x=lon, method='nearest').compute()
    
    # 转换为Pandas DataFrame以便于计算和写入
    df = cell_data.to_dataframe()
    
    # --- 7. 单位换算与参数计算 ---
    df_out = pd.DataFrame(index=df.index) # 创建一个新的DataFrame用于存储最终结果
    
    # 1. 气温 (air_temp): 从 K 转换为 °C
    df_out['air_temp'] = df['temp'] - 273.15

    # 2. 降水 (prec): 从 kg/m2/s (即 mm/s) 转换为 mm/day
    df_out['prec'] = df['prec'] * 86400

    # 3. 气压 (pressure): 从 Pa 转换为 kPa
    df_out['pressure'] = df['pres'] / 1000.0

    # 4. 短波辐射 (swdown): 单位 W/m2，仅重命名
    df_out['swdown'] = df['srad']
    
    # 5. 长波辐射 (lwdown): 单位 W/m2，仅重命名
    df_out['lwdown'] = df['lrad']

    # 6. 水汽压 (vp): 根据比湿(shum)和气压(pres)计算，并转换为kPa
    df_out['vp'] = (df['shum'] * df['pres']) / (0.622 + 0.378 * df['shum']) / 1000.0
    
    # 7. 风速 (wind): 单位 m/s，无需转换
    df_out['wind'] = df['wind']

    # --- 8. 整理并写入文件 ---
    # 严格按照您指定的顺序选择最终的列
    final_columns_order = ['air_temp', 'prec', 'pressure', 'swdown', 'lwdown', 'vp', 'wind']
    vic_forcing_df = df_out[final_columns_order]
    
    # 将数据写入文本文件，使用制表符 '\t' 作为分隔符，保留4位小数
    vic_forcing_df.to_csv(
        output_path,
        sep='\t',
        header=False,
        index=False,
        float_format='%.4f'
    )

print("\n全部处理成功完成！")
print(f"已在 '{OUTPUT_FORCING_DIR}' 文件夹下生成 {num_grids} 个气象驱动文件。")