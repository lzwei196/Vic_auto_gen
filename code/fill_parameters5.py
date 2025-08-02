import pandas as pd
from pathlib import Path
import os

# --- 1. 配置路径 ---
# 输入文件：您上一步生成的文件
SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\soil_param_with_met.txt")

# 输出文件：本次更新后的最终文件
SOIL_PARAM_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\soil_param_with_resid.txt")

# --- 2. 准备工作 ---
print("处理开始...")
if not SOIL_PARAM_IN.exists():
    print(f"错误: 找不到输入文件 {SOIL_PARAM_IN}")
    exit()

# --- 3. 读取并更新数据 ---
print(f"正在读取文件: {SOIL_PARAM_IN.name}")
# 读取时指定所有列为字符串(object)，以保留原始格式
df_soil = pd.read_csv(SOIL_PARAM_IN, sep=' ', header=None, dtype=object)

print("正在将第50, 51, 52列的值设置为 0 ...")
# 列号50, 51, 52 对应的DataFrame索引是 49, 50, 51
columns_to_update = [49, 50, 51]
df_soil.loc[:, columns_to_update] = 0

print("参数更新完毕！")

# --- 4. 按精确格式保存更新后的文件 ---
print(f"正在将更新后的文件保存至: {SOIL_PARAM_OUT.name}")
with open(SOIL_PARAM_OUT, 'w') as f:
    # 逐行处理DataFrame
    for index, row in df_soil.iterrows():
        # 将行转换为列表
        items = list(row)
        formatted_items = []
        
        # 遍历行中的每一项进行格式化
        for i, item in enumerate(items):
            item_str = str(item)
            
            # 第1, 2列 (整数)
            if i in [0, 1]:
                formatted_items.append(str(int(float(item_str))))
            # 第3, 4列: lat, lon (4位小数)
            elif i in [2, 3]:
                formatted_items.append(f"{float(item_str):.4f}")
            # 第22列: elev (2位小数)
            elif i == 21:
                formatted_items.append(f"{float(item_str):.2f}")
            # 其他所有列
            else:
                try:
                    num = float(item_str)
                    if num == -9999.0:
                        formatted_items.append('-9999')
                    elif num == int(num):
                        formatted_items.append(str(int(num)))
                    else:
                        # 默认保留3位小数
                        formatted_items.append(f"{num:.3f}")
                except ValueError:
                    formatted_items.append(item_str)
        
        f.write(" ".join(formatted_items) + "\n")

print("\n操作成功完成！")
print(f"已生成新文件: {SOIL_PARAM_OUT}")