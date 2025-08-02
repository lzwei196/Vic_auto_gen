import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path
import os

# --- 1. 配置 ---
# 提供一个您已处理好的NC文件路径，脚本将用它来定义格网
NC_FILE_PATH = Path(r"H:\CMFD\huai\Data_forcing_01dy_010deg\wind_CMFD_V0200_B-01_01dy_025deg_202001-202012_huai.nc")

# **关键修改**: 更新为您指定的输出路径和文件名
OUTPUT_SOIL_FILE = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\vic_soil_param.txt")

# --- 2. 准备工作 ---
# 确保输出文件夹存在
os.makedirs(OUTPUT_SOIL_FILE.parent, exist_ok=True)
print(f"输出文件将被保存至: {OUTPUT_SOIL_FILE}")

# --- 3. 从NC文件提取格网信息 ---
print(f"正在从 {NC_FILE_PATH.name} 读取格网信息...")
try:
    with xr.open_dataset(NC_FILE_PATH) as ds:
        print("正在从 (y, x) 维度提取格网...")
        grid_points = ds[list(ds.data_vars)[0]].stack(gridcell=('y', 'x')).dropna('gridcell', how='all')
        df_grid = pd.DataFrame({
            'lat': grid_points.coords['y'].values,
            'lon': grid_points.coords['x'].values
        })
except FileNotFoundError:
    print(f"错误：找不到NC文件 '{NC_FILE_PATH}'，请确保路径和文件名正确。")
    exit()
except KeyError as e:
    print(f"错误: 在文件中找不到预期的维度名称 'y' 或 'x'。收到的错误是 {e}。")
    exit()
print(f"成功提取了 {len(df_grid)} 个格网单元。")

# --- 4. 创建完整的土壤参数DataFrame ---
num_columns = 53
df_soil = pd.DataFrame(np.full((len(df_grid), num_columns), -9999.0))
print("已创建包含53列的土壤参数文件框架。")

# --- 5. 填充已知的基础信息 ---
print("正在填充基础信息...")
# **关键修改**: 调整第1列和第2列的顺序
df_soil.iloc[:, 0] = 1                              # 第1列: Run flag (网格是否运行)
df_soil.iloc[:, 1] = np.arange(1, len(df_grid) + 1) # 第2列: Cell number (网格号)
df_soil.iloc[:, 2] = df_grid['lat']                 # 第3列: lat
df_soil.iloc[:, 3] = df_grid['lon']                 # 第4列: lon
print("基础信息填充完毕。")

# --- 6. 自定义格式化并写入文件 ---
# **关键修改**: 重写文件保存逻辑以满足精确的格式要求
print(f"\n正在进行精确格式化并写入文件...")
try:
    with open(OUTPUT_SOIL_FILE, 'w') as f:
        # 逐行处理DataFrame
        for index, row in df_soil.iterrows():
            formatted_items = []
            # 格式化每一列的数据
            # 第1列: Run flag (整数)
            formatted_items.append(str(int(row.iloc[0])))
            # 第2列: Cell number (整数)
            formatted_items.append(str(int(row.iloc[1])))
            # 第3列: lat (保留4位小数)
            formatted_items.append(f"{row.iloc[2]:.4f}")
            # 第4列: lon (保留4位小数)
            formatted_items.append(f"{row.iloc[3]:.4f}")
            
            # 处理剩余的所有列 (从第5列开始)
            for item in row.iloc[4:]:
                # 检查是否为整数
                if item == int(item):
                    formatted_items.append(str(int(item)))
                else:
                    # 如果是小数，保留3位小数
                    formatted_items.append(f"{item:.3f}")
            
            # 用空格连接所有格式化后的字符串，并写入文件
            f.write(" ".join(formatted_items) + "\n")

    print("\n操作成功完成！")
    print(f"模板文件 '{OUTPUT_SOIL_FILE.name}' 已在指定路径生成。")

except Exception as e:
    print(f"\n写入文件时发生错误: {e}")