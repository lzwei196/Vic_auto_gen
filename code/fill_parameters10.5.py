import pandas as pd
import numpy as np
from pathlib import Path
import os
import warnings

# --- 0. 忽略不必要的警告 ---
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 1. 配置路径 ---
SOIL_PARAM_IN = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL_COMPLETE.txt")
ARCGIS_SOIL_OUTPUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\source_data\soil\arcgis_output_soil.txt")
SOIL_PARAM_OUT = Path(r"C:\Users\yc\Desktop\vic\huaihe\F_F\vic\param\SOIL_PARAM_FINAL.txt")

# --- 2. PTF(土壤转换函数) 定义，基于 Saxton & Rawls (2006) ---
def calculate_soil_params_from_texture(sand, clay):
    if pd.isna(sand) or pd.isna(clay) or (sand + clay > 100) or sand < 0 or clay < 0:
        return {'expt': 4.0, 'bulk_density': 1300, 'Wpwp_FRACT': 0.1, 'Wcr_FRACT': 0.25, 'Ksat': 10}
        
    sand_frac = max(0.01, sand / 100.0)
    clay_frac = max(0.01, clay / 100.0)

    # 凋零点 (Wilting Point, 1500 kPa)
    wp_t1 = -0.024 * sand_frac + 0.487 * clay_frac + 0.006 * (sand_frac * clay_frac) + 0.005 * (sand_frac**2) * clay_frac + 0.013 * sand_frac * (clay_frac**2)
    Wpwp_FRACT = max(0.01, wp_t1 + 0.14 * wp_t1 - 0.02)
    
    # 田间持水量 (Field Capacity, 33 kPa)
    fc_t1 = -0.251 * sand_frac + 0.195 * clay_frac + 0.011 * (sand_frac * clay_frac) + 0.006 * (sand_frac**2) * clay_frac - 0.027 * sand_frac * (clay_frac**2)
    Wcr_FRACT = max(0.02, fc_t1 + 0.14 * fc_t1 - 0.02)
    
    if Wcr_FRACT <= Wpwp_FRACT: Wcr_FRACT = Wpwp_FRACT + 0.02

    # 孔隙度 (Porosity)
    porosity_t = 0.332 - 0.7251 * sand_frac + 0.1276 * np.log10(clay_frac)
    porosity = max(0.01, porosity_t + (0.02 * porosity_t**2) * np.exp(-2.5 * sand_frac))
    
    if porosity <= Wcr_FRACT: porosity = Wcr_FRACT + 0.02

    # Expt (b) - Clapp and Hornberger "b" parameter
    b = (np.log(1500) - np.log(33)) / (np.log(Wcr_FRACT) - np.log(Wpwp_FRACT))
    expt = 2 * b + 3
    if expt <= 3.0: expt = 3.1 # 强制确保expt > 3.0

    # Ksat (饱和导水率, mm/day)
    lambda_param = 1 / b
    Ksat_mm_hr = max(0.1, 1930 * ((porosity - Wcr_FRACT)**(3 - lambda_param)))
    
    # 容重 (Bulk Density)
    bulk_density = (1 - porosity) * 2650 # kg/m3

    return {
        'expt': expt, 'bulk_density': bulk_density, 'Wpwp_FRACT': Wpwp_FRACT,
        'Wcr_FRACT': Wcr_FRACT, 'Ksat': Ksat_mm_hr * 24
    }

# --- 3. 准备工作 ---
print("最终参数生成脚本(PTF物理模型版)开始...")
if not SOIL_PARAM_IN.exists() or not ARCGIS_SOIL_OUTPUT.exists():
    print(f"错误: 找不到输入文件，请检查路径。"); exit()
os.makedirs(SOIL_PARAM_OUT.parent, exist_ok=True)

# --- 4. 读取数据 ---
print(f"正在读取文件: {SOIL_PARAM_IN.name} 和 {ARCGIS_SOIL_OUTPUT.name}")
df_soil = pd.read_csv(SOIL_PARAM_IN, sep=' ', header=None, dtype=object)
df_soil.columns = [f'col_{i+1}' for i in range(df_soil.shape[1])]
df_arcgis = pd.read_csv(ARCGIS_SOIL_OUTPUT, sep=',')

# --- 5. 提取主导土壤的砂粒和粘粒含量 ---
print("正在提取主导土壤的砂粒/粘粒含量...")
max_share_indices = df_arcgis.groupby('grid_id')['SHARE'].idxmax(skipna=True).dropna()
dominant_soil_info = df_arcgis.loc[max_share_indices]
dominant_soil_info = dominant_soil_info.set_index('grid_id')[['T_SAND', 'T_CLAY', 'S_SAND', 'S_CLAY']]

df_soil['col_2'] = df_soil['col_2'].astype(int)
df_soil = df_soil.merge(dominant_soil_info, left_on='col_2', right_index=True, how='left')
print("砂粒/粘粒含量提取完毕。")

# --- 6. 根据PTF公式重新计算并填充土壤水力参数 ---
print("正在根据PTF公式重新计算并填充所有土壤水力参数...")
for index, row in df_soil.iterrows():
    params_t = calculate_soil_params_from_texture(row['T_SAND'], row['T_CLAY'])
    params_s = calculate_soil_params_from_texture(row['S_SAND'], row['S_CLAY'])
    
    # 填充 Expt, Ksat, Bulk Density, Wcr, Wpwp
    df_soil.loc[index, ['col_10', 'col_11']] = params_t['expt']; df_soil.loc[index, 'col_12'] = params_s['expt']
    df_soil.loc[index, ['col_13', 'col_14']] = params_t['Ksat']; df_soil.loc[index, 'col_15'] = params_s['Ksat']
    df_soil.loc[index, ['col_34', 'col_35']] = params_t['bulk_density']; df_soil.loc[index, 'col_36'] = params_s['bulk_density']
    df_soil.loc[index, ['col_41', 'col_42']] = params_t['Wcr_FRACT']; df_soil.loc[index, 'col_43'] = params_s['Wcr_FRACT']
    df_soil.loc[index, ['col_44', 'col_45']] = params_t['Wpwp_FRACT']; df_soil.loc[index, 'col_46'] = params_s['Wpwp_FRACT']
    # 填充 init_moist
    df_soil.loc[index, ['col_19', 'col_20']] = params_t['Wcr_FRACT'] * 0.5; df_soil.loc[index, 'col_21'] = params_s['Wcr_FRACT'] * 0.5

print("土壤水力参数重新计算并填充完毕。")

# --- 7. 按精确格式保存最终文件 ---
print(f"\n正在写入最终文件: {SOIL_PARAM_OUT.name}")
final_df = df_soil.iloc[:, :53]
with open(SOIL_PARAM_OUT, 'w') as f:
    for index, row in final_df.iterrows():
        formatted_items = []
        for i, item in enumerate(row):
            try:
                num = float(item)
                if num == int(num): formatted_items.append(str(int(num)))
                else: formatted_items.append(f"{num:.2f}")
            except (ValueError, TypeError): formatted_items.append(str(item))
        f.write(" ".join(formatted_items) + "\n")

print("\n所有任务成功完成！恭喜您，最终的土壤参数文件已生成！")