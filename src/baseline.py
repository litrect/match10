"""ResNet-18 training baseline. Smoke mode does not measure convergence."""
import argparse,csv,json,random,time
from pathlib import Path
import numpy as np
import torch,torchvision
from torch.utils.data import DataLoader
from torchvision.models import resnet18,ResNet18_Weights
from src.dataset import ChestDataset,read_manifest,aggregate_studies,metrics
ROOT=Path(__file__).resolve().parents[1]

def save_json(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def evaluate(model,loader,device):
 model.eval(); ids=[]; probs=[]; labels=[]
 with torch.inference_mode():
  for batch in loader:
   x=batch['image'].to(device,non_blocking=True)
   with torch.autocast('cuda',dtype=torch.float16): logits=model(x)
   p=torch.sigmoid(logits.float()).cpu().numpy()
   if not np.isfinite(p).all(): raise RuntimeError('Non-finite predictions')
   ids.extend(batch['study_id']); probs.append(p); labels.append(batch['target'].numpy())
 return aggregate_studies(ids,np.concatenate(probs),np.concatenate(labels))

def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--smoke',action='store_true'); parser.add_argument('--epochs',type=int,default=5); parser.add_argument('--batch-size',type=int,default=4); parser.add_argument('--workers',type=int,default=2); parser.add_argument('--train-batches',type=int,default=4); parser.add_argument('--size',type=int,default=320); parser.add_argument('--lr',type=float,default=1e-4); parser.add_argument('--seed',type=int,default=42); parser.add_argument('--weights',choices=['imagenet','none'],default='imagenet'); parser.add_argument('--run-name',default=None); args=parser.parse_args()
 if args.epochs<1 or args.batch_size<1 or args.train_batches<1: parser.error('Positive counts required')
 random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
 if not torch.cuda.is_available(): raise RuntimeError('CUDA required; use project .venv')
 torch.cuda.manual_seed_all(args.seed); torch.set_num_threads(4)
 cfg=json.loads((ROOT/'configs/project_paths.json').read_text(encoding='utf-8')); policy=json.loads((ROOT/'configs/training_policy.json').read_text(encoding='utf-8'))
 if policy['data_usage']['merge_validation_into_training']: raise ValueError('Validation must remain separate')
 manifests=ROOT/cfg['manifests_dir']; train=read_manifest(manifests/'train.csv'); valid=read_manifest(manifests/'valid.csv')
 assert {r['Subject_id'] for r in train}.isdisjoint({r['Subject_id'] for r in valid})
 assert all(r['split']=='train' for r in train) and all(r['split']=='valid' for r in valid)
 if args.smoke: train=random.Random(args.seed).sample(train,min(len(train),args.batch_size*args.train_batches))
 run_name=args.run_name or ('smoke_' if args.smoke else 'baseline_')+time.strftime('%Y%m%d_%H%M%S'); out=ROOT/'reports/training'/run_name; model_dir=ROOT/'models'/run_name
 if out.exists() or model_dir.exists(): raise FileExistsError('Choose a new run name')
 out.mkdir(parents=True); model_dir.mkdir(parents=True)
 torch.hub.set_dir(str(ROOT/'artifacts/torch_cache'))
 weights=ResNet18_Weights.IMAGENET1K_V1 if args.weights=='imagenet' else None
 print('Loading model weights',flush=True); model=resnet18(weights=weights); model.fc=torch.nn.Linear(model.fc.in_features,10); model=model.cuda()
 optimizer=torch.optim.AdamW(model.parameters(),lr=args.lr,weight_decay=1e-4); scaler=torch.amp.GradScaler('cuda'); criterion=torch.nn.BCEWithLogitsLoss()
 train_loader=DataLoader(ChestDataset(ROOT,train,args.size,True),batch_size=args.batch_size,shuffle=True,num_workers=args.workers,pin_memory=True)
 valid_loader=DataLoader(ChestDataset(ROOT,valid,args.size,False),batch_size=args.batch_size,num_workers=args.workers,pin_memory=True)
 metadata={'args':vars(args),'python_environment':'project .venv','torch':torch.__version__,'torchvision':torchvision.__version__,'gpu':torch.cuda.get_device_name(0),'pretrained_source':weights.url if weights else None,'class_order':list(range(1,11)),'train_images':len(train),'validation_images':len(valid),'validation_used_for_training':False,'aggregation':'mean image probabilities per Study_id','preprocess':'RGB; train rotation +/-5 degrees; aspect-preserving resize and black padding; ImageNet normalization','scope':'pipeline smoke test, not converged performance' if args.smoke else 'baseline training'}
 save_json(out/'config.json',metadata); best=-1; history=[]; start=time.time(); torch.cuda.reset_peak_memory_stats()
 for epoch in range(1,(1 if args.smoke else args.epochs)+1):
  model.train(); loss_sum=0.; count=0
  for step,batch in enumerate(train_loader,1):
   optimizer.zero_grad(set_to_none=True); x=batch['image'].cuda(non_blocking=True); y=batch['target'].cuda(non_blocking=True)
   with torch.autocast('cuda',dtype=torch.float16): loss=criterion(model(x),y)
   if not torch.isfinite(loss): raise RuntimeError('Non-finite training loss')
   scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update(); loss_sum+=loss.item()*len(x); count+=len(x)
   if step%100==0 or args.smoke:
    print(f'Epoch {epoch} step {step}/{len(train_loader)} loss {loss.item():.4f}',flush=True)
    save_json(out/'progress.json',{'status':'training','epoch':epoch,'total_epochs':1 if args.smoke else args.epochs,'step':step,'steps_per_epoch':len(train_loader),'train_loss_running':loss_sum/count,'elapsed_seconds':round(time.time()-start,1)})
  print('Evaluating full independent validation set',flush=True); ids,p,t=evaluate(model,valid_loader,'cuda'); scores=metrics(p,t)
  torch.save({'model_state':model.state_dict(),'optimizer_state':optimizer.state_dict(),'scaler_state':scaler.state_dict(),'epoch':epoch,'metadata':metadata},model_dir/'last.pt')
  record={'epoch':epoch,'train_loss':loss_sum/count,**scores}; history.append(record); save_json(out/'history.json',history); print(json.dumps(record),flush=True)
  score=scores['macro_auc']
  if score is not None and score>best:
   best=score; checkpoint=model_dir/'best.pt'; torch.save({'model_state':model.state_dict(),'metadata':metadata,'epoch':epoch,'metrics':scores},checkpoint)
   with (out/'validation_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['Study_id']+[f'prob_{i}' for i in range(1,11)]+[f'label_{i}' for i in range(1,11)])
    for sid,pr,tr in zip(ids,p,t): w.writerow([sid]+pr.tolist()+tr.astype(int).tolist())
 # Verify exact state restoration using the final in-memory state, independent of best epoch.
 reload_path=model_dir/'reload_check.pt'; torch.save(model.state_dict(),reload_path); probe=next(iter(valid_loader))['image'].cuda(); model.eval()
 with torch.inference_mode(): before=model(probe)
 restored=resnet18(weights=None,num_classes=10).cuda(); restored.load_state_dict(torch.load(reload_path,map_location='cuda',weights_only=True)); restored.eval()
 with torch.inference_mode(): after=restored(probe)
 torch.testing.assert_close(before,after,rtol=0,atol=0); reload_path.unlink()
 result={'status':'PASS','mode':'smoke' if args.smoke else 'training','epochs_completed':len(history),'validation_studies':len(ids),'all_10_auc_classes_valid':scores['auc_valid_classes']==10,'best_macro_auc':best,'checkpoint':str(checkpoint.relative_to(ROOT)),'checkpoint_size_MB':round(checkpoint.stat().st_size/1e6,2),'save_reload_exact_match':True,'elapsed_seconds':round(time.time()-start,1),'peak_allocated_MiB':round(torch.cuda.max_memory_allocated()/1024**2,1),'note':'Smoke results only verify the pipeline and do not indicate trained model quality.' if args.smoke else 'Official T4 latency not tested.'}
 save_json(out/'progress.json',{'status':'completed','epochs_completed':len(history),'best_macro_auc':best}); save_json(out/'result.json',result); print(json.dumps(result),flush=True)
if __name__=='__main__': main()
