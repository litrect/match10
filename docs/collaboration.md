# 协作者启动指南

## 准备数据与环境

1. 接受私有仓库邀请后，克隆仓库。已有副本先执行git pull。
2. 通过赛事允许的方式准备原始数据，放入项目根目录dataset下，包含train、valid、test和对应CSV。
3. 使用Python 3.12创建独立环境，安装以下依赖。不要复制其他电脑的.venv。

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/environment/verify_gpu.py
```

先确认python --version为3.12；如有多个版本，使用Python 3.12解释器的完整路径创建环境。需要支持相应CUDA版本的NVIDIA驱动。网络代理按自己的电脑配置。
精确版本可参考requirements-training-lock.txt，该锁文件来自Windows Python 3.12环境。

## RTX4050 6GB流程测试

```powershell
.\.venv\Scripts\python.exe -m src.baseline --smoke --batch-size 2 --workers 2 --run-name collaborator_4050_smoke_v1
```

此配置尚未在4050实测。通过后可尝试batch size 4；显存不足时减小批量，读取多进程报错时改为--workers 0。冒烟测试只做4次更新并评估完整验证集，不代表模型最终效果。

完整训练示例：

```powershell
.\.venv\Scripts\python.exe -m src.baseline --epochs 5 --batch-size 4 --workers 2 --run-name collaborator_4050_baseline_v1
```

训练耗时需以自己电脑实测为准。保持电脑供电并避免休眠。

## 协作约定

- 使用独立Git分支和独立run-name，不覆盖其他人的实验目录。
- train用于参数训练，valid仅用于调参和评估，不并入训练；共同使用仓库中的数据清单与类别顺序。
- 比较结果时报告批量大小、学习率、种子、模型和输入尺寸；批量不同会影响实验可比性。
- 优先提交代码、配置、history.json、result.json及分析报告；原始数据、虚拟环境和下载缓存不提交。
- 完成的有价值最佳模型可另行共享；当前仓库不含只做4次更新的测试模型。
- 原始数据不随GitHub分发；报告中的历史本机绝对路径仅作记录，代码使用相对路径清单。
- 当前模型训练程序不支持直接通过命令行断点续训。每轮结束保存last.pt和best.pt；在首轮结束前停止不会生成可恢复检查点。

已有4060上的GPU和真实数据流程测试报告仅说明该电脑测试通过，不代表4050已验证。最新完整基线运行曾按用户要求停止，尚无完整训练成绩。
