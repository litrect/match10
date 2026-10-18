# 胸部 X 光片多标签分类比赛

## 目录说明

| 目录 | 用途 |
|---|---|
| `dataset/` | 原始数据，包括 train、valid、test 图像和对应 CSV；保持现有位置 |
| `configs/` | 类别映射和项目路径配置 |
| `docs/` | 比赛实施计划等文档 |
| `scripts/data/` | 数据检查与处理脚本 |
| `scripts/docs/` | 文档生成脚本 |
| `reports/dataset_audit/` | 数据统计、抽样患者和图像核验报告 |
| `src/` | 后续模型、训练、评估和推理代码 |
| `models/` | 后续保存的模型权重 |
| `submissions/` | 后续生成的比赛提交文件 |
| `artifacts/document_build/` | 文档制作及排版检查中间文件 |

## 使用约定

- 原始数据保留不变，生成结果写入对应输出目录。
- `configs/project_paths.json` 中的路径均相对于项目根目录。
- 类别映射使用 `configs/class_mapping.json`；CSV版本便于直接查看。
- 标签向量按类别1至10排列，原始多标签字段使用分号分隔。
- 数据检查入口为 `scripts/data/audit_dataset.py`，输出到 `reports/dataset_audit/`。
- 数据检查脚本按文件位置定位根目录，可从不同工作目录运行；需要 Pillow。
- 抽样种子为20261018。当前报告的图像解码检查仅覆盖10名患者的17张图像；元数据检查覆盖全部CSV。
- 文档生成入口为 `scripts/docs/build_plan.py`，需要 python-docx，输出到 `docs/`。

## 训练方案约定

- 训练策略配置为 `configs/training_policy.json`，后续开发遵循该配置。
- 按用户项目设定，允许使用ImageNet等通用预训练权重及医学预训练权重；这项设定尚非组委会正式确认。记录权重来源与版本，便于复现。
- 仅使用train进行参数训练，valid用于调参、模型选择、评估和阈值选择；任何阶段均不得将valid并入训练。
- 测试集自监督或伪标签、模型融合与测试时增强、计时及体积测量细则暂不纳入当前方案，不能视作已获准。

## 全量图像完整性检查

- 脚本：`scripts/data/check_image_integrity.py`。
- 报告：`reports/image_integrity/report.md`，逐图结果：`image_results.csv`，异常清单：`issues.csv`。
- 已检查33984张图像，全部通过CSV对应、严格完整解码与尺寸核对；未发现缺失、额外图像或重复CSV记录。
- 全部图像均为JPEG灰度图。本检查不包含医学标签正确性或图像内容哈希去重。

## GitHub共享范围

仓库保存除原始数据和本机凭据等文件之外的全部项目材料，包括代码、配置、计划文档、检查报告、模型、提交文件和中间文件。原始数据及其压缩包由.gitignore排除。首次克隆后，在项目根目录创建dataset目录并放入赛事数据，目录下应包含train、valid、test及对应CSV；再创建本地输出目录或运行检查脚本自动生成报告。

安装当前工具依赖：`python -m pip install -r requirements.txt`。
运行全量完整性检查：`python scripts/data/check_image_integrity.py`。
