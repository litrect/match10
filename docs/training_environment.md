# match10 独立训练环境

环境目录：项目根目录下的`.venv`，使用Python 3.12。

## 使用

在项目根目录的PowerShell中激活：

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/environment/verify_gpu.py
```

也可不激活，直接指定解释器：

```powershell
.\.venv\Scripts\python.exe scripts/environment/verify_gpu.py
```

编辑器的Python解释器选择`.venv\Scripts\python.exe`。如果激活脚本受PowerShell策略限制，直接指定解释器即可。

## 重建

用已有Python 3.12创建环境，然后安装：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\.venv\Scripts\python.exe scripts/environment/verify_gpu.py
```

安装需要可访问官方软件源。网络代理按各自电脑配置，不将本机代理地址写为协作者的默认配置。
`.venv`不上传GitHub；依赖说明和验证脚本用于协作者重建环境。
GPU冒烟测试使用随机初始化模型和合成数据，不下载预训练权重，也不启动正式训练。

## 已完成验证

Python 3.12.9，torch 2.10.0+cu128，torchvision 0.25.0+cu128；CUDA可用，pip check无依赖冲突。ResNet-18以320×320输入、batch size 2完成一次混合精度前向、反向和参数更新。
精确版本锁定文件：requirements-training-lock.txt，可在新建环境中使用`python -m pip install -r requirements-training-lock.txt`重建；版本锁针对当前Windows Python 3.12环境。
