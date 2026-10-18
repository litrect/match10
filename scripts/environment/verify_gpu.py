"""Verify CUDA forward/backward with a small 10-label classifier."""
import json,sys,time
from pathlib import Path
import torch,torchvision
from torchvision.models import resnet18
ROOT=Path(__file__).resolve().parents[2]
def main():
 if not torch.cuda.is_available(): raise RuntimeError('CUDA is not available')
 torch.manual_seed(42); device=torch.device('cuda'); torch.cuda.reset_peak_memory_stats()
 model=resnet18(weights=None,num_classes=10).to(device).train()
 optimizer=torch.optim.AdamW(model.parameters(),lr=1e-4)
 x=torch.randn(2,3,320,320,device=device); target=torch.randint(0,2,(2,10),device=device).float()
 start=time.time(); optimizer.zero_grad(set_to_none=True)
 with torch.autocast(device_type='cuda',dtype=torch.float16):
  logits=model(x); loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,target)
 scaler=torch.amp.GradScaler('cuda'); scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update(); torch.cuda.synchronize()
 assert torch.isfinite(loss).item()
 assert any(p.grad is not None and torch.isfinite(p.grad).all().item() for p in model.parameters())
 result={'python':sys.version.split()[0],'executable':sys.executable,'torch':torch.__version__,'torchvision':torchvision.__version__,'cuda_build':torch.version.cuda,'cudnn':torch.backends.cudnn.version(),'gpu':torch.cuda.get_device_name(0),'gpu_memory_bytes':torch.cuda.get_device_properties(0).total_memory,'cuda_available':True,'smoke_test':'PASS','model':'resnet18 random initialization','batch_size':2,'input_shape':[2,3,320,320],'output_shape':list(logits.shape),'loss':loss.item(),'mixed_precision':True,'peak_allocated_MiB':round(torch.cuda.max_memory_allocated()/1024**2,1),'seconds':round(time.time()-start,2),'note':'One synthetic batch forward/backward only; not training quality or official T4 latency validation.'}
 out=ROOT/'reports/environment'; out.mkdir(parents=True,exist_ok=True); (out/'gpu_smoke_test.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
