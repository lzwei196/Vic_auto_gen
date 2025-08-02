# VIC模型淮河流域输入数据处理脚本

本仓库包含一套为VIC（Variable Infiltration Capacity）模型准备淮河流域（Huaihe Basin）标准输入数据的Python脚本。

## 项目简介

该项目旨在自动化处理原始的地理、气象和植被数据，最终生成VIC模型所需的三大核心输入文件：

1.  气象驱动文件 (Forcing Files)
2.  土壤参数文件 (Soil Parameter File)
3.  植被参数文件 (Vegetation Parameter File)

## 脚本执行流程

本仓库中的脚本之间存在严格的执行顺序和文件依赖关系。**在运行前，请务必详细阅读工作流说明文档**，其中详细描述了每个脚本的功能、输入输出和执行顺序。

**-> [点击这里查看详细工作流说明 (WORKFLOW.md)](WORKFLOW.md)**

## 环境设置

所有必要的Python库已在 `requirements.txt` 文件中列出。请使用以下命令创建虚拟环境并安装依赖：

```bash
# 创建并激活虚拟环境 (推荐)
python -m venv venv
source venv/bin/activate  # on Linux/Mac
# venv\Scripts\activate  # on Windows

# 安装依赖
pip install -r requirements.txt