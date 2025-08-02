import xarray as xr
import pandas as pd
from pathlib import Path
import os
import warnings

# --- 0. 忽略不必要的警告 ---
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 1. 配置路径 ---
# 输入文件：您已经填充好部分参数的土壤文件
SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\soil_param_updated.txt")

# 输入文件夹：包含所有处理好的1991-2020年prec气象文件的文件夹
MET_DATA_DIR = Path(r"H:\CMFD\huai\Data_forcing_01dy_010deg")

# 输出文件：本次更新后的最终文件
SOIL_PARAM_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\soil_param_with_met.txt")

# --- 2. 准备工作 ---
print("处理开始...")
if not SOIL_PARAM_IN.exists():
    print(f"错误: 找不到输入文件 {SOIL_PARAM_IN}"); exit()
if not MET_DATA_DIR.exists():
    print(f"错误: 找不到气象数据文件夹 {MET_DATA_DIR}"); exit()

# --- 3. 读取数据 ---
print(f"正在读取土壤参数文件: {SOIL_PARAM_IN.name}")
df_soil = pd.read_csv(SOIL_PARAM_IN, sep=' ', header=None, dtype=object)
df_soil.columns = [f'col_{i}' for i in range(df_soil.shape[1])]

# --- 4. 计算并填充年平均降水 ---
print("正在计算年平均降水...")
try:
    prec_files_pattern = "prec_*_huai.nc"
    prec_files_path = MET_DATA_DIR / prec_files_pattern
    print(f"正在从路径 {MET_DATA_DIR} 中查找并读取匹配 '{prec_files_pattern}' 的所有降水文件...")
    
    with xr.open_mfdataset(str(prec_files_path), chunks='auto') as ds_prec:
        prec_var = list(ds_prec.data_vars)[0]

        # ====================================================================
        # --- 关键修正: 增加单位换算 ---
        # ====================================================================
        # 1. 计算30年的平均降水率 (假定原始单位为: mm/s)
        print("正在计算多年平均降水率(mm/s)...")
        mean_prec_rate_mm_per_sec = ds_prec[prec_var].mean(dim='time').compute()
        
        # 2. 将单位从 mm/s 转换为 mm/day
        # 一天有 60秒/分钟 * 60分钟/小时 * 24小时/天 = 86400 秒
        print("正在将单位从 mm/s 转换为 mm/day...")
        mean_prec_mm_per_day = mean_prec_rate_mm_per_sec * 86400
        
        # 3. 计算年平均总降水量 (单位: mm/year)
        print("正在计算年平均总降水量(mm/year)...")
        annual_prec = mean_prec_mm_per_day * 365.25
        # ====================================================================

        # 4. 为土壤文件中的每一个点，精确获取年平均降水量
        print("正在为每个格网匹配降水值...")
        lats = df_soil.iloc[:, 2].astype(float).values
        lons = df_soil.iloc[:, 3].astype(float).values
        lats_to_find = xr.DataArray(lats, dims="points")
        lons_to_find = xr.DataArray(lons, dims="points")
        
        prec_values = annual_prec.sel(y=lats_to_find, x=lons_to_find, method="nearest")
        final_prec_values = prec_values.fillna(0.0).values
        
        # 5. 填充到第49列 (索引为48)
        df_soil.iloc[:, 48] = final_prec_values
        print("年平均降水填充完毕！")

except Exception as e:
    print(f"错误：在处理降水文件时发生错误。请确保路径下有匹配 '{prec_files_pattern}' 的文件。错误信息: {e}")
    exit()

# --- 5. 按精确格式保存更新后的文件 ---
print(f"正在将更新后的文件保存至: {SOIL_PARAM_OUT.name}")
df_soil_to_write = df_soil.astype(object)
with open(SOIL_PARAM_OUT, 'w') as f:
    for index, row in df_soil_to_write.iterrows():
        formatted_items = []
        for i, item in enumerate(row):
            item_str = str(item)
            if i in [0, 1]: formatted_items.append(str(int(float(item_str))))
            elif i in [2, 3]: formatted_items.append(f"{float(item_str):.4f}")
            elif i == 21: formatted_items.append(f"{float(item_str):.2f}")
            else:
                num = float(item_str)
                if num == -9999.0: formatted_items.append('-9999')
                elif num == int(num): formatted_items.append(str(int(num)))
                else: formatted_items.append(f"{num:.3f}")
        
        f.write(" ".join(formatted_items) + "\n")

print("\n操作成功完成！")
print(f"已生成新文件: {SOIL_PARAM_OUT}")