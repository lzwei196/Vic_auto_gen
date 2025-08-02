import pandas as pd
import xarray as xr
from pathlib import Path
import os
import warnings

# --- 0. 忽略不必要的警告 ---
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 1. 配置路径 ---
# 【输入文件1】您已填充好部分参数的土壤文件
SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL.txt")
# 【输入文件2】您的全球5分分辨率土壤数据文件
GLOBAL_SOIL_FILE = Path(r"C:\Users\yc\Desktop\vic\coach\spaw土壤计算等多个文件\土壤5分数据\global_soil_param_new.txt")
# 【输出文件】本次任务的最终成果
SOIL_PARAM_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL_COMPLETE.txt")

# --- 2. 定义源数据和目标数据的列映射 ---
# 源文件(global_soil_param_new.txt)中，参数所在的列索引 (从0开始)
SOURCE_COLS = {
    'lat': 2, 'lon': 3,
    'AVG_T': 25, 'init_moist_1': 18, 'init_moist_2': 19, 'init_moist_3': 20,
    'QUARTZ_1': 30, 'QUARTZ_2': 31, 'QUARTZ_3': 32,
}
# 目标文件(SOIL_PARAM_FINAL.txt)中，需要被填充的列索引 (从0开始)
TARGET_COLS = {
    'AVG_T': 25, 'init_moist_1': 18, 'init_moist_2': 19, 'init_moist_3': 20,
    'QUARTZ_1': 30, 'QUARTZ_2': 31, 'QUARTZ_3': 32,
}

# --- 3. 准备工作 ---
print("最终参数填充脚本开始...")
if not SOIL_PARAM_IN.exists() or not GLOBAL_SOIL_FILE.exists():
    print(f"错误: 找不到输入文件，请检查路径。"); exit()
os.makedirs(SOIL_PARAM_OUT.parent, exist_ok=True)

# --- 4. 读取数据 ---
print(f"正在读取全球土壤数据: {GLOBAL_SOIL_FILE.name}")
try:
    df_global = pd.read_csv(GLOBAL_SOIL_FILE, sep=r'\s+', header=None, usecols=list(SOURCE_COLS.values()))
    df_global.columns = SOURCE_COLS.keys()
except Exception as e:
    print(f"错误：读取全球土壤文件失败。请检查文件格式和列配置。错误信息: {e}"); exit()

print(f"正在读取待填充的土壤文件: {SOIL_PARAM_IN.name}")
df_soil = pd.read_csv(SOIL_PARAM_IN, sep=' ', header=None, dtype=object)
df_soil.columns = [f'col_{i+1}' for i in range(df_soil.shape[1])]

# --- 5. 循环插值并填充每一个参数 ---
print("正在为所有目标参数进行空间插值...")
# 获取目标格网的经纬度
lats_to_find = xr.DataArray(df_soil['col_3'].astype(float).values, dims="points")
lons_to_find = xr.DataArray(df_soil['col_4'].astype(float).values, dims="points")

# 循环为每个需要填充的参数进行插值
for param_name, vic_col_index in TARGET_COLS.items():
    print(f"  - 正在处理参数: {param_name} -> 第 {vic_col_index+1} 列")
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
        interp_values = source_da.interp(lat=lats_to_find, lon=lons_to_find, method="linear")
        
        # 4. 用0填充可能因边界效应产生的NaN值
        final_values = interp_values.fillna(0.0).values
        
        # 5. 将插值结果填充到目标DataFrame中
        df_soil.iloc[:, vic_col_index] = final_values
    except Exception as e:
        print(f"    - 警告：处理参数 {param_name} 时出错，该列将保持-9999。错误: {e}")

print("所有缺失参数插值填充完毕！")

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

print("\n所有任务成功完成！最终土壤参数文件已生成。")