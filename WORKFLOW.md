# VIC 模型数据处理工作流

本文档旨在说明如何按顺序运行本仓库中的Python脚本，以生成VIC模型所需的输入文件。

**重要提示**: 在运行任何脚本之前，请务必检查并修改脚本内部配置的输入和输出文件路径，使其符合您本地的目录结构。

---

### 流程一：准备基础地理与气象数据

此流程处理最原始的地理和气象数据，为后续所有步骤提供标准化的输入。

#### 步骤 1: 预处理CMFD气象数据

* [cite_start]**脚本**: `forcing.py` [cite: 1]
* [cite_start]**功能**: 根据淮河流域的Shapefile，裁剪并筛选1991-2020年份的全国CMFD气象数据（风速、气温、降水等），并将其重采样至0.25度分辨率 [cite: 1, 3, 5, 6]。
* **输入**:
    * [cite_start]原始0.1度分辨率的全国CMFD `.nc` 文件 [cite: 1]。
    * [cite_start]淮河流域边界文件 `huaihe.shp` [cite: 1]。
* **输出**:
    * [cite_start]一系列裁剪并重采样后的 `..._huai.nc` 文件，存放于 `H:\CMFD\huai\Data_forcing_01dy_010deg` [cite: 1]。

#### 步骤 2: 预处理高程数据

* **脚本**: `process_elevation.py`
* [cite_start]**功能**: 与步骤1类似，专门用于裁剪和重采样全国高程数据 [cite: 12, 13]。
* **输入**:
    * [cite_start]原始0.1度分辨率的全国高程 `.nc` 文件 (`elev_CMFD...nc`) [cite: 12]。
    * [cite_start]淮河流域边界文件 `huaihe.shp` [cite: 12]。
* **输出**:
    * [cite_start]裁剪并重采样后的淮河流域高程文件 `elev..._huai.nc` [cite: 13]。

---

### 流程二：生成模型输入文件

此流程基于预处理好的数据，生成VIC模型可直接读取的植被和气象驱动文件。

#### 步骤 3: 生成植被参数文件

* [cite_start]**脚本**: `process_vegetation_detailed.py` [cite: 129]
* [cite_start]**功能**: 基于一个标准格网文件，结合高分辨率植被覆盖图和植被库文件，通过空间统计（zonal_stats）为每个格网生成植被覆盖参数 [cite: 133, 134, 135]。
* **输入**:
    * [cite_start]主格网文件（如 `wind..._huai.nc`） [cite: 129]。
    * [cite_start]高分辨率植被栅格图 `AVHRR...tif` [cite: 129]。
    * [cite_start]植被库文件 `veglib.LDAS` [cite: 129]。
* **输出**:
    * [cite_start]VIC植被参数文件 `vic_veg_param_final.txt` [cite: 129]。

#### 步骤 4: 生成日尺度气象驱动文件

* **脚本**: `process_forcing.py`
* [cite_start]**功能**: 读取流程一中生成的所有 `..._huai.nc` 文件，进行单位换算（如K转°C，Pa转kPa，mm/s转mm/day），并为每个有效格网生成一个VIC格式的文本驱动文件 [cite: 104, 106, 107]。
* **输入**:
    * [cite_start]流程一输出的所有 `..._huai.nc` 文件 [cite: 103]。
* **输出**:
    * [cite_start]649个日尺度气象驱动文件，存放于 `forcing` 文件夹 [cite: 105]。

#### 步骤 5 (可选): 生成6小时尺度驱动文件

* **脚本**: `disaggregate_forcing.py`
* [cite_start]**功能**: 将日尺度的驱动文件通过简单的均分或重复方法，转换为6小时尺度 [cite: 127, 128]。
* **输入**:
    * [cite_start]步骤4输出的所有日尺度驱动文件 [cite: 126]。
* **输出**:
    * [cite_start]649个6小时尺度驱动文件，存放于 `forcing_6H` 文件夹 [cite: 126]。

---

### 流程三：生成土壤参数文件 (分步法)

此流程通过一系列脚本链，逐步构建和填充最终的土壤参数文件。后一步脚本的输入是前一步的输出。

#### 步骤 6: 逐步填充与计算

* **1. 创建基础框架**:
    * [cite_start]**脚本**: `framework.py` [cite: 15]
    * [cite_start]**输入**: 任意一个 `..._huai.nc` 文件（用于定义格网） [cite: 15]。
    * [cite_start]**输出**: `vic_soil_param.txt`，一个仅包含格网号和经纬度的基础文件 [cite: 16, 18]。

* **2. 填充常量**:
    * **脚本**: `fill_parameters2.py`, `fill_parameters3.py`
    * **输入**: 上一步的输出文件。
    * [cite_start]**输出**: `soil_param_with_constants.txt` -> `soil_param_updated.txt`，逐步填充了深度、Dp等常量 [cite: 34, 38]。

* **3. 填充年均降水**:
    * [cite_start]**脚本**: `fill_parameters4.py` [cite: 45]
    * [cite_start]**输入**: `soil_param_updated.txt` 和所有 `prec_*_huai.nc` 文件 [cite: 45]。
    * [cite_start]**输出**: `soil_param_with_met.txt`，填充了第49列的年均降水 [cite: 48, 51]。

* **4. 填充其余参数 (PTF物理模型法)**:
    * [cite_start]**脚本**: `fill_parameters10.5.py` [cite: 109]
    * [cite_start]**功能**: **这是最关键的一步**。它读取上一步的中间文件和ArcGIS输出的土壤质地文件，应用Saxton & Rawls (2006)物理公式，重新计算并覆盖所有核心土壤水力参数（如Expt, Ksat, Wcr, Wpwp, Bulk_density） [cite: 112, 114, 115, 116, 117, 118]。
    * **输入**:
        * [cite_start]中间土壤文件（如`SOIL_PARAM_FINAL_COMPLETE.txt`） [cite: 109]。
        * [cite_start]包含砂粒/粘粒含量的 `arcgis_output_soil.txt` [cite: 109]。
    * [cite_start]**输出**: `SOIL_PARAM_FINAL.txt` **(最终土壤参数文件)** [cite: 113]。

* **5. (备选/探索性) 其他填充方法**:
    * [cite_start]**说明**: `fill_parameters6.py` 到 `fill_parameters10.py` 等脚本使用了不同的方法（如 `mdata` 查找表或全局数据插值）来填充水力参数 [cite: 63, 73, 82, 96]。由于最终采用了PTF物理模型法，这些脚本可视为**已废弃的探索性代码**，仅供参考。