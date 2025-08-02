import pandas as pd
from pathlib import Path
import os
import warnings

# --- 1. 配置路径 ---
# 输入文件：包含高程、降水和部分常量的土壤文件
SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\soil_param_with_resid.txt")

# 输入文件：ArcGIS生成的、包含详细土壤质地信息的文件
ARCGIS_SOIL_OUTPUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\source_data\soil\arcgis_output_soil.txt")

# 输出文件：最终的、完整的土壤参数文件
SOIL_PARAM_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL.txt")

# --- 2. 准备工作 ---
print("最终参数填充脚本开始...")
if not SOIL_PARAM_IN.exists() or not ARCGIS_SOIL_OUTPUT.exists():
    print(f"错误: 找不到输入文件，请检查路径。")
    exit()

# --- 3. 读取数据 ---
print(f"正在读取文件: {SOIL_PARAM_IN.name} 和 {ARCGIS_SOIL_OUTPUT.name}")
df_soil = pd.read_csv(SOIL_PARAM_IN, sep=' ', header=None, dtype=object)
df_soil.columns = [f'col_{i+1}' for i in range(df_soil.shape[1])]
df_arcgis = pd.read_csv(ARCGIS_SOIL_OUTPUT, sep=',')

# --- 4. 提取主导土壤质地ID ---
print("正在为每个格网计算主导的表层土壤质地...")
safe_mode = lambda x: x.mode().iloc[0] if not x.mode().empty else 1
# 我们现在只需要表层土壤质地
dominant_textures = df_arcgis.groupby('grid_id')[['T_USDA_TEX_CLASS']].agg(safe_mode).reset_index()

df_soil['col_2'] = df_soil['col_2'].astype(int)
dominant_textures['grid_id'] = dominant_textures['grid_id'].astype(int)

df_soil = pd.merge(df_soil, dominant_textures, left_on='col_2', right_on='grid_id', how='left')
df_soil['T_USDA_TEX_CLASS'].fillna(1, inplace=True)
soil_code_t = df_soil['T_USDA_TEX_CLASS'].astype(int).tolist()
print("主导表层土壤质地提取完毕。")


# --- 5. 根据“单层剖面”逻辑填充所有剩余参数 ---
print("正在根据“单层剖面”逻辑填充所有剩余参数...")
# 5.1 参数查找表 [ID, Ksat, Wcr, Wpwp, Expt, Bulk_density]
mdata = {
    1: [1,0,0,0,0,0], 2: [2,708,0.37,0.25,21.868,1400], 3: [3,763.2,0.36,0.17,27.691,1260], 4: [4,1096.8,0.36,0.21,15.195,0],
    5: [5,424.8,0.34,0.21,16.888,1350], 6: [6,2061.6,0.28,0.08,8.509,0], 7: [7,950.4,0.32,0.12,11.064,1380], 8: [8,285.6,0.31,0.23,12.302,0],
    9: [9,472.8,0.29,0.14,13.362,1410], 10: [10,576,0.27,0.17,18.152,1410], 11: [11,1257.6,0.21,0.09,12.524,1480],
    12: [12,2608.8,0.15,0.06,11.888,1660], 13: [13,9218.4,0.08,0.03,11.734,1740]
}

# 5.2 填充常量
df_soil['col_5'] = 0.3; df_soil['col_6'] = 0.02; df_soil['col_7'] = 10.00; df_soil['col_8'] = 0.7; df_soil['col_9'] = 2
df_soil['col_47'] = 0.01; df_soil['col_48'] = 0.03;

# 5.3 查表填充 (所有三层都使用表层土壤质地 soil_code_t)
# mdata索引: [1]Ksat, [2]Wcr, [3]Wpwp, [4]Expt, [5]Bulk_density
df_soil['col_10'] = df_soil['col_11'] = df_soil['col_12'] = [mdata.get(tid, mdata[1])[4] for tid in soil_code_t] # expt
df_soil['col_13'] = df_soil['col_14'] = df_soil['col_15'] = [mdata.get(tid, mdata[1])[1] for tid in soil_code_t] # ksat
df_soil['col_34'] = df_soil['col_35'] = df_soil['col_36'] = [mdata.get(tid, mdata[1])[5] for tid in soil_code_t] # BULKDEN
df_soil['col_41'] = df_soil['col_42'] = df_soil['col_43'] = [mdata.get(tid, mdata[1])[2] for tid in soil_code_t] # Wcr_fract
df_soil['col_44'] = df_soil['col_45'] = df_soil['col_46'] = [mdata.get(tid, mdata[1])[3] for tid in soil_code_t] # Wpwp_fract

# 5.4 填充剩余的占位符和计算值
df_soil.loc[:, [15, 16, 17, 27, 28, 29, 30, 31, 32]] = -9999.0 # PHI_s, BUBLE, QUARTZ (按要求保留-9999或暂无数据)
df_soil['col_19'] = df_soil['col_41'].astype(float) * 0.5 # init_moist 1
df_soil['col_20'] = df_soil['col_42'].astype(float) * 0.5 # init_moist 2
df_soil['col_21'] = df_soil['col_43'].astype(float) * 0.5 # init_moist 3
df_soil['col_54'] = -9999.0  # JULY_TAVG (设为-9999标准占位符)
print("所有参数填充完毕。")

# --- 6. 按精确格式保存最终文件 ---
print(f"\n正在写入最终文件: {SOIL_PARAM_OUT.name}")
final_df = df_soil.iloc[:, :53]
with open(SOIL_PARAM_OUT, 'w') as f:
    for index, row in final_df.iterrows():
        formatted_items = []
        for i, item in enumerate(row):
            col_number = i + 1
            item_str = str(item)
            try:
                num = float(item_str)
                # 对整数进行特殊处理
                if num == int(num):
                    formatted_items.append(str(int(num)))
                # 对所有其他小数保留两位
                else:
                    formatted_items.append(f"{num:.2f}")
            except ValueError:
                formatted_items.append(item_str)
        f.write(" ".join(formatted_items) + "\n")

print("\n所有任务成功完成！最终土壤参数文件已生成。")