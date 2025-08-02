import pandas as pd
from pathlib import Path
import os
import warnings

# --- 0. 忽略不必要的警告 ---
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 1. 配置路径 ---
# 输入文件1：您上一步生成，已包含部分常量的文件
SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL_v2.txt")

# 输入文件2：您在ArcGIS中生成的、包含详细土壤质地信息的文件
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
print("正在为每个格网计算主导的表层和下层土壤质地...")

# ====================================================================
# --- 关键修正: 增加对SHARE列全为NaN的格网的处理 ---
# 1. 找到每组中SHARE最大的行的索引
max_share_indices = df_arcgis.groupby('grid_id')['SHARE'].idxmax(skipna=True)
# 2. 丢弃那些因为没有有效SHARE而返回NaN的组
valid_indices = max_share_indices.dropna()
# 3. 根据有效的索引提取完整的行信息
dominant_soil_indices = df_arcgis.loc[valid_indices]
# ====================================================================

dominant_textures = dominant_soil_indices[['grid_id', 'T_USDA_TEX_CLASS', 'S_USDA_TEX_CLASS']].set_index('grid_id')

# 将主文件中的格网ID转换为整数，以便合并
df_soil['col_2'] = df_soil['col_2'].astype(int)
# 这里使用 .map() 方法，它比 merge 更适合这种基于索引的查找
df_soil['T_USDA_TEX_CLASS'] = df_soil['col_2'].map(dominant_textures['T_USDA_TEX_CLASS'])
df_soil['S_USDA_TEX_CLASS'] = df_soil['col_2'].map(dominant_textures['S_USDA_TEX_CLASS'])

# 对于没有在arcgis_output中找到对应信息的格网（例如那些全NaN的），填充默认值1
df_soil['T_USDA_TEX_CLASS'].fillna(1, inplace=True)
df_soil['S_USDA_TEX_CLASS'].fillna(1, inplace=True)

soil_code_t = df_soil['T_USDA_TEX_CLASS'].astype(int).tolist()
soil_code_s = df_soil['S_USDA_TEX_CLASS'].astype(int).tolist()
print("主导土壤质地提取完毕。")


# --- 5. 根据R代码逻辑填充所有剩余参数 ---
print("正在根据土壤质地填充水力参数...")
mdata = {
    1:  [1, 0, 0, 0, 0, 0], 2: [2, 708, 0.37, 0.25, 21.868, 1400],
    3:  [3, 763.2, 0.36, 0.17, 27.691, 1260], 4: [4, 1096.8, 0.36, 0.21, 15.195, 0],
    5:  [5, 424.8, 0.34, 0.21, 16.888, 1350], 6: [6, 2061.6, 0.28, 0.08, 8.509, 0],
    7:  [7, 950.4, 0.32, 0.12, 11.064, 1380], 8: [8, 285.6, 0.31, 0.23, 12.302, 0],
    9:  [9, 472.8, 0.29, 0.14, 13.362, 1410], 10: [10, 576, 0.27, 0.17, 18.152, 1410],
    11: [11, 1257.6, 0.21, 0.09, 12.524, 1480], 12: [12, 2608.8, 0.15, 0.06, 11.888, 1660],
    13: [13, 9218.4, 0.08, 0.03, 11.734, 1740]
}
# mdata 索引: [1]Ksat, [2]Wcr_fract, [3]Wpwp_fract, [4]Expt, [5]BULKDEN

df_soil['col_5'] = 0.3; df_soil['col_6'] = 0.02; df_soil['col_7'] = 10.00; df_soil['col_8'] = 0.7; df_soil['col_9'] = 2
df_soil['col_47'] = 0.01; df_soil['col_48'] = 0.03

df_soil['col_10'] = [mdata.get(tid, mdata[1])[4] for tid in soil_code_t]; df_soil['col_11'] = df_soil['col_10']; df_soil['col_12'] = [mdata.get(tid, mdata[1])[4] for tid in soil_code_s]
df_soil['col_13'] = [mdata.get(tid, mdata[1])[1] for tid in soil_code_t]; df_soil['col_14'] = df_soil['col_13']; df_soil['col_15'] = [mdata.get(tid, mdata[1])[1] for tid in soil_code_s]
df_soil['col_34'] = [mdata.get(tid, mdata[1])[5] for tid in soil_code_t]; df_soil['col_35'] = df_soil['col_34']; df_soil['col_36'] = [mdata.get(tid, mdata[1])[5] for tid in soil_code_s]
df_soil['col_41'] = [mdata.get(tid, mdata[1])[2] for tid in soil_code_t]; df_soil['col_42'] = df_soil['col_41']; df_soil['col_43'] = [mdata.get(tid, mdata[1])[2] for tid in soil_code_s]
df_soil['col_44'] = [mdata.get(tid, mdata[1])[3] for tid in soil_code_t]; df_soil['col_45'] = df_soil['col_44']; df_soil['col_46'] = [mdata.get(tid, mdata[1])[3] for tid in soil_code_s]

df_soil.loc[:, [15, 16, 17, 18, 19, 20, 27, 28, 29, 30, 31, 32]] = -9999.0 
df_soil['col_54'] = -9999.0
print("所有参数填充完毕。")

# --- 6. 按精确格式保存最终文件 ---
print(f"\n正在写入最终文件: {SOIL_PARAM_OUT.name}")
final_df = df_soil.iloc[:, :53]
with open(SOIL_PARAM_OUT, 'w') as f:
    for index, row in final_df.iterrows():
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