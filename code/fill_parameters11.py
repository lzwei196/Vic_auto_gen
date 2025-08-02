import pandas as pd
from pathlib import Path
import os

# --- 1. 配置路径 ---
# 输入文件：您需要修改的土壤参数文件
SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL.txt")

# 输出文件：格式化之后的新文件
SOIL_PARAM_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL_formatted.txt")

# --- 2. 准备工作 ---
print("开始格式化经纬度...")
if not SOIL_PARAM_IN.exists():
    print(f"错误: 找不到输入文件 {SOIL_PARAM_IN}")
    exit()
os.makedirs(SOIL_PARAM_OUT.parent, exist_ok=True)

# --- 3. 读取、格式化并保存文件 ---
try:
    # **关键步骤**: 使用 dtype=object 读取所有数据为字符串，以保留原始格式
    print(f"正在读取文件: {SOIL_PARAM_IN.name}")
    df_soil = pd.read_csv(SOIL_PARAM_IN, sep=' ', header=None, dtype=object, skip_blank_lines=False)

    # 对第3列（纬度，索引为2）和第4列（经度，索引为3）进行格式化
    # .map() 方法可以对列中的每一个元素应用格式化函数
    print("正在格式化第3列 (纬度) 和第4列 (经度) 为四位小数...")
    df_soil.iloc[:, 2] = df_soil.iloc[:, 2].astype(float).map('{:.4f}'.format)
    df_soil.iloc[:, 3] = df_soil.iloc[:, 3].astype(float).map('{:.4f}'.format)
    
    # **关键步骤**: 将修改后的DataFrame写回文本文件，保持空格分隔，不加表头和索引
    print(f"正在将结果保存到新文件: {SOIL_PARAM_OUT.name}")
    df_soil.to_csv(SOIL_PARAM_OUT, sep=' ', header=False, index=False, quotechar='"', lineterminator='\n')
    
    print("\n操作成功完成！")
    print(f"已生成格式化后的新文件: {SOIL_PARAM_OUT}")

except Exception as e:
    print(f"处理过程中发生错误: {e}")