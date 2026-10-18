# 模型数据清单

train.csv和valid.csv每张图像一行，label_1至label_10按类别1至10排列。test.csv无标签列，禁止将未知标签作为全0处理。
image_path相对于项目根目录，代码需用项目根目录拼接，不依赖当前工作目录。
保留Subject_id和Study_id，评估和提交时必须按Study_id汇总图像预测。
训练集仅在同一患者同次检查内按SHA-256去重，每组保留Dicom_id字典序最小的图像，排除明细见excluded_duplicates.csv。原始文件不变。
验证集与测试集保持完整，验证集不得并入训练。
重建入口：scripts/data/build_manifests.py；依赖全量哈希报告reports/image_duplicates/image_hashes.csv。
