import pandas as pd
from pathlib import Path
import os

# --- 1. 配置路径 ---
# 输入文件：您已经填充好高程的土壤参数文件
SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\soil_param_final.txt")

# 输出文件：填充了更多参数的新文件
SOIL_PARAM_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\soil_param_with_constants.txt")

# --- 2. 定义要填充的常量值 ---
# {列索引: 要填充的值}
# 第23列(索引22) -> Depth(1)
# 第24列(索引23) -> Depth(2)
# 第25列(索引24) -> Depth(3)
# 第27列(索引26) -> Dp
# 第40列(索引39) -> Off_gmt
# 第53列(索引52) -> Fs_active
CONSTANTS_TO_FILL = {
    22: 0.1,
    23: 1.0,
    24: 1.5,
    26: 3.0,
    39: 8,
    52: 1
}

# --- 3. 准备工作 ---
print("处理开始...")
if not SOIL_PARAM_IN.exists():
    print(f"错误: 找不到输入文件 {SOIL_PARAM_IN}")
    exit()

# --- 4. 读取并填充数据 ---
print(f"正在读取文件: {SOIL_PARAM_IN.name}")
# 读取时指定所有列为字符串(object)，以保留原始格式，避免pandas自动转换类型
df_soil = pd.read_csv(SOIL_PARAM_IN, sep=' ', header=None, dtype=object)

print("正在填充模型常量参数...")
for col_index, value in CONSTANTS_TO_FILL.items():
    # 使用 .loc 进行赋值，这是pandas推荐的方式
    df_soil.loc[:, col_index] = value

print("常量参数填充完毕！")

# --- 5. 保存为与之前完全一致的精确格式 ---
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
            # 第3,4列(索引2,3): lat, lon (保留4位小数)
            if i in [2, 3]:
                formatted_items.append(f"{float(item_str):.4f}")
            # 第22列(索引21): elev (保留2位小数)
            elif i == 21:
                formatted_items.append(f"{float(item_str):.2f}")
            # 其他列保持原样（已经是填充好的整数或-9999）
            else:
                formatted_items.append(item_str)
        
        # 用空格连接所有格式化后的字符串，并写入文件
        f.write(" ".join(formatted_items) + "\n")

print("\n操作成功完成！")