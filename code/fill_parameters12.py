import pandas as pd
from pathlib import Path
import os

# --- 1. 配置路径 ---
# 输入文件：您需要修改的土壤参数文件
SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL_formatted.txt")

# 输出文件：坐标平移之后的新文件
SOIL_PARAM_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL_shifted.txt")

# --- 2. 定义坐标偏移量 ---
LAT_SHIFT = 0.0050
LON_SHIFT = -0.0050

# --- 3. 准备工作 ---
print("坐标平移脚本开始...")
if not SOIL_PARAM_IN.exists():
    print(f"错误: 找不到输入文件 {SOIL_PARAM_IN}")
    exit()
os.makedirs(SOIL_PARAM_OUT.parent, exist_ok=True)

# --- 4. 读取、处理并保存文件 ---
try:
    # **关键步骤**: 使用 dtype=object 读取所有数据为字符串，以保留其他列的原始格式
    print(f"正在读取文件: {SOIL_PARAM_IN.name}")
    df_soil = pd.read_csv(SOIL_PARAM_IN, sep=' ', header=None, dtype=object, skip_blank_lines=False)

    # 为经纬度列（第3和第4列，索引为2和3）进行数学运算
    print(f"正在对纬度(第3列)加上 {LAT_SHIFT}...")
    # 先转换为浮点数，进行计算
    df_soil.iloc[:, 2] = df_soil.iloc[:, 2].astype(float) + LAT_SHIFT

    print(f"正在对经度(第4列)加上 {LON_SHIFT}...")
    df_soil.iloc[:, 3] = df_soil.iloc[:, 3].astype(float) + LON_SHIFT
    
    # **关键步骤**: 将修改后的DataFrame写回文本文件，并应用最终格式
    print(f"正在将结果保存到新文件: {SOIL_PARAM_OUT.name}")
    with open(SOIL_PARAM_OUT, 'w') as f:
        for index, row in df_soil.iterrows():
            formatted_items = []
            for i, item in enumerate(row):
                # 第3和第4列（索引2和3）是我们修改过的，需要格式化为4位小数
                if i in [2, 3]:
                    formatted_items.append(f"{float(item):.4f}")
                # 其他所有列，直接使用从文件中读取时的原始字符串，不做任何改动
                else:
                    formatted_items.append(str(item))
            
            f.write(" ".join(formatted_items) + "\n")
    
    print("\n操作成功完成！")
    print(f"已生成坐标平移后的新文件: {SOIL_PARAM_OUT}")

except Exception as e:
    print(f"处理过程中发生错误: {e}")