import sys,importlib.util,json
print('PYTHON',sys.executable,sys.version.split()[0],flush=True)
print('PACKAGES',json.dumps({x:bool(importlib.util.find_spec(x)) for x in ['torch','torchvision','timm','numpy','pandas','sklearn','PIL','yaml']}),flush=True)
if importlib.util.find_spec('torch'):
 import torch
 print('TORCH',torch.__version__,'BUILD_CUDA',torch.version.cuda,'CUDA_AVAILABLE',torch.cuda.is_available(),flush=True)
 if torch.cuda.is_available():
  x=torch.randn(512,512,device='cuda'); y=x@x; torch.cuda.synchronize()
  print('GPU',torch.cuda.get_device_name(0),'MATMUL_OK',bool(torch.isfinite(y).all().item()),flush=True)
