# ResNet18 基线使用说明

## 数据与模型

- 数据入口为data/manifests中的train.csv和valid.csv，验证患者与训练患者强制分离。
- 灰度胸片转为3通道；保持比例缩放并黑色填充为320×320；使用ImageNet归一化。
- 训练仅增加正负5度以内随机旋转，验证不使用随机增强。
- ResNet18使用官方ImageNet IMAGENET1K_V1初始化，分类头替换为10输出。
- BCEWithLogitsLoss训练；Sigmoid输出10类概率；同次检查的多图概率平均。
- 每个epoch在完整验证集计算检查级Macro-AUC、每类AUC和0.5阈值Macro-F1。
- 按验证Macro-AUC保存最佳模型，验证数据不参与参数更新。

## 先验证完整流程

```powershell
.\.venv\Scripts\python.exe -m src.baseline --smoke
```

默认抽取16张训练图像，以batch size 4执行4次参数更新，再评估全部1422张验证图像、859次检查。此时指标仅用于验证流程，不代表模型已经学好。
程序会保存模型，再验证保存与重新加载后的预测完全一致。

## 完整基线训练

```powershell
.\.venv\Scripts\python.exe -m src.baseline --epochs 5 --batch-size 4 --workers 2
```

在项目根目录运行。输出位于models和reports/training下独立命名的运行目录，不覆盖已有运行。权重首次从官方源下载，后续使用artifacts/torch_cache缓存。
workers可设为0排查Windows多进程读取问题；batch size和分辨率需要根据实际训练显存再调整。

目前未实现断点续训、测试集预测文件导出、阈值调优和正式T4延迟测量。
