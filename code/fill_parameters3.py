import pandas as pd
from pathlib import Path
import os

# --- 1. 配置路径 ---
# 输入文件：您上一步生成的文件
SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\soil_param_with_constants.txt")

# 输出文件：本次更新后的最终文件
SOIL_PARAM_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\soil_param_updated.txt")

# --- 2. 定义要更新的参数值 ---
# {列索引: 要填充的值}
# VIC参数文件列号从1开始，而程序中索引从0开始，所以列号需要减1
UPDATES = {
    26: 4.00,   # 第27列: Dp
    36: 2685,   # 第37列: soil_density_1
    37: 2685,   # 第38列: soil_density_2
    38: 2685,   # 第39列: soil_density_3
    52: 0,      # 第53列: Fs_active
    22: 0.1,    # 第23列: Depth(1)
    23: -9999,  # 第24列: Depth(2)
    24: -9999,  # 第25列: Depth(3)
}

# --- 3. 准备工作 ---
print("处理开始...")
if not SOIL_PARAM_IN.exists():
    print(f"错误: 找不到输入文件 {SOIL_PARAM_IN}")
    exit()

# --- 4. 读取并更新数据 ---
print(f"正在读取文件: {SOIL_PARAM_IN.name}")
# 读取时指定所有列为字符串(object)，以保留原始格式，避免pandas自动转换类型
try:
    df_soil = pd.read_csv(SOIL_PARAM_IN, sep=' ', header=None, dtype=object)
except Exception as e:
    print(f"读取文件时出错，请确保文件内容是空格分隔的。错误: {e}")
    exit()

print("正在更新指定的参数列...")
for col_index, value in UPDATES.items():
    # 使用 .loc 进行赋值，这是pandas推荐的方式
    df_soil.loc[:, col_index] = value

print("参数更新完毕！")

# --- 5. 按精确格式保存更新后的文件 ---
print(f"正在将更新后的文件保存至: {SOIL_PARAM_OUT.name}")
with open(SOIL_PARAM_OUT, 'w') as f:
    # 逐行处理DataFrame
    for index, row in df_soil.iterrows():
        # 将行转换为列表，方便按索引修改
        items = list(row)
        formatted_items = []
        
        # 遍历行中的每一项
        for i, item in enumerate(items):
            # 将所有项转换为字符串
            item_str = str(item)
            
            # 对特定列应用特定格式，其他列保持原样
            # 第3,4列(索引2,3): lat, lon (4位小数)
            if i in [2, 3]:
                formatted_items.append(f"{float(item_str):.4f}")
            # 第22列(索引21): elev (2位小数)
            elif i == 21:
                formatted_items.append(f"{float(item_str):.2f}")
            # 其他所有列，根据其值判断格式
            else:
                try:
                    # 尝试转换为浮点数
                    num = float(item_str)
                    # 如果是整数值 (例如 1.0, 8.0, -9999.0)，则格式化为整数
                    if num == int(num):
                        formatted_items.append(str(int(num)))
                    # 否则，格式化为3位小数（适用于Dp等）
                    else:
                        formatted_items.append(f"{num:.3f}")
                except ValueError:
                    # 如果无法转换为数字，则保持原样（虽然在此脚本中不太可能发生）
                    formatted_items.append(item_str)
        
        # 用空格连接所有格式化后的字符串，并写入文件
        f.write(" ".join(formatted_items) + "\n")

print("\n操作成功完成！")
print(f"已生成新文件: {SOIL_PARAM_OUT}")