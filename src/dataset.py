"""Image-level loading with study-level multi-label evaluation."""
import csv,random
from pathlib import Path
import numpy as np
import torch
from PIL import Image,ImageOps
from torch.utils.data import Dataset
from torchvision.transforms import functional as TF

LABELS=[f'label_{i}' for i in range(1,11)]

def read_manifest(path):
 with Path(path).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

class ChestDataset(Dataset):
 def __init__(self,root,rows,size=320,training=False):
  self.root=Path(root); self.rows=rows; self.size=size; self.training=training
 def __len__(self): return len(self.rows)
 def __getitem__(self,index):
  r=self.rows[index]
  with Image.open(self.root/r['image_path']) as im:
   image=im.convert('RGB')
  if self.training:
   image=TF.rotate(image,random.uniform(-5,5),interpolation=TF.InterpolationMode.BILINEAR,fill=0)
  image=ImageOps.pad(image,(self.size,self.size),method=Image.Resampling.BILINEAR,color=0,centering=(0.5,0.5))
  tensor=TF.normalize(TF.to_tensor(image),[0.485,0.456,0.406],[0.229,0.224,0.225])
  item={'image':tensor,'study_id':r['Study_id'],'subject_id':r['Subject_id'],'dicom_id':r['Dicom_id']}
  if all(k in r for k in LABELS): item['target']=torch.tensor([float(r[k]) for k in LABELS])
  return item

def aggregate_studies(study_ids,probabilities,targets):
 grouped={}
 for sid,p,t in zip(study_ids,probabilities,targets):
  if sid not in grouped: grouped[sid]=[[],t]
  if not np.array_equal(grouped[sid][1],t): raise ValueError(f'Inconsistent labels: {sid}')
  grouped[sid][0].append(p)
 ids=sorted(grouped)
 return ids,np.stack([np.mean(grouped[s][0],axis=0) for s in ids]),np.stack([grouped[s][1] for s in ids])

def metrics(probabilities,targets):
 from sklearn.metrics import roc_auc_score,f1_score
 auc=[]
 for c in range(10):
  auc.append(float(roc_auc_score(targets[:,c],probabilities[:,c])) if len(np.unique(targets[:,c]))==2 else None)
 return {'macro_auc':float(np.mean([x for x in auc if x is not None])) if any(x is not None for x in auc) else None,'per_class_auc':{str(i+1):x for i,x in enumerate(auc)},'auc_valid_classes':sum(x is not None for x in auc),'macro_f1_at_0_5':float(f1_score(targets,probabilities>=0.5,average='macro',zero_division=0))}
