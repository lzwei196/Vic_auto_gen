import pandas as pd
import xarray as xr
from pathlib import Path
import os
import warnings

# --- 0. 忽略不必要的警告 ---
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 1. 配置路径 ---
# 【输入文件1】您已填充好部分参数的土壤文件
SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL_COMPLETE.txt")

# 【输入文件2】您的全球5分分辨率土壤数据文件
GLOBAL_SOIL_FILE = Path(r"C:\Users\yc\Desktop\vic\coach\spaw土壤计算等多个文件\土壤5分数据\global_soil_param_new.txt")

# 【输出文件】本次任务的最终成果
SOIL_PARAM_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL_v2.txt")

# --- 2. 定义源数据和目标数据的列映射 ---
# 源文件(global...)中参数所在的列索引 (从0开始) vs 目标文件(SOIL_PARAM...)中要填充的列索引
PARAMS_TO_INTERPOLATE = {
    # 参数名: {源文件列索引, 目标文件列索引(可能多个)}
    'expt':           {'source_col': 9, 'target_cols': [9, 10, 11]},
    'ksat':           {'source_col': 12, 'target_cols': [12, 13, 14]},
    'bulk_density':   {'source_col': 33, 'target_cols': [33, 34, 35]},
    'Wcr_FRACT':      {'source_col': 40, 'target_cols': [40, 41, 42]},
    'Wpwp_FRACT':     {'source_col': 43, 'target_cols': [43, 44, 45]},
}
# 从映射中获取所有需要读取的源文件列
source_cols_to_read = [2, 3] + [v['source_col'] for v in PARAMS_TO_INTERPOLATE.values()]
source_col_names = ['lat', 'lon'] + list(PARAMS_TO_INTERPOLATE.keys())

# --- 3. 准备工作 ---
print("最终参数填充脚本开始...")
if not SOIL_PARAM_IN.exists() or not GLOBAL_SOIL_FILE.exists():
    print(f"错误: 找不到输入文件，请检查路径。"); exit()
os.makedirs(SOIL_PARAM_OUT.parent, exist_ok=True)

# --- 4. 读取数据 ---
print(f"正在读取全球土壤数据: {GLOBAL_SOIL_FILE.name}")
try:
    df_global = pd.read_csv(GLOBAL_SOIL_FILE, sep=r'\s+', header=None, usecols=source_cols_to_read, dtype=float)
    df_global.columns = source_col_names
except Exception as e:
    print(f"错误：读取全球土壤文件失败。请检查文件格式和列配置。错误信息: {e}"); exit()

print(f"正在读取待更新的土壤文件: {SOIL_PARAM_IN.name}")
df_soil = pd.read_csv(SOIL_PARAM_IN, sep=' ', header=None, dtype=object)
df_soil.columns = [f'col_{i+1}' for i in range(df_soil.shape[1])]

# --- 5. 循环插值并填充每一个参数 ---
print("正在为所有目标参数进行空间插值...")
lats_to_find = xr.DataArray(df_soil['col_3'].astype(float).values, dims="points")
lons_to_find = xr.DataArray(df_soil['col_4'].astype(float).values, dims="points")

# **关键修正**: 逐个参数构建插值格网并进行插值
for param_name, details in PARAMS_TO_INTERPOLATE.items():
    print(f"  - 正在处理参数: {param_name}...")
    try:
        # 1. 为当前参数构建专用的2D数据
        df_param_pivot = df_global.pivot_table(index='lat', columns='lon', values=param_name)
        
        # 2. 转换为xarray.DataArray
        source_da = xr.DataArray(
            df_param_pivot.values,
            coords=[df_param_pivot.index, df_param_pivot.columns],
            dims=['lat', 'lon']
        )
        source_da = source_da.reindex(lat=list(reversed(source_da.lat)))

        # 3. 执行线性插值
        interp_values = source_da.interp(lat=lats_to_find, lon=lons_to_find, method="linear").fillna(0.0).values
        
        # 4. 将插值结果填充到所有对应的目标列
        for vic_col_index in details['target_cols']:
            df_soil.iloc[:, vic_col_index] = interp_values
            
    except Exception as e:
        print(f"    - 警告：处理参数 {param_name} 时出错，该列将保持不变。错误: {e}")

print("所有指定参数的插值与替换完成！")

# --- 6. 按精确格式保存最终文件 ---
print(f"\n正在写入最终文件: {SOIL_PARAM_OUT.name}")
with open(SOIL_PARAM_OUT, 'w') as f:
    for index, row in df_soil.iterrows():
        formatted_items = []
        for i, item in enumerate(row):
            item_str = str(item)
            try:
                num = float(item_str)
                if num == int(num):
                    formatted_items.append(str(int(num)))
                else:
                    formatted_items.append(f"{num:.2f}")
            except ValueError:
                formatted_items.append(item_str)
        f.write(" ".join(formatted_items) + "\n")

print("\n所有任务成功完成！恭喜您，最终的土壤参数文件已生成！")