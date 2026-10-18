"""Build reproducible image manifests; deduplicate train within each study."""
import csv,json
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
def write(path,rows,fields):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def main():
 cfg=json.loads((ROOT/'configs/project_paths.json').read_text(encoding='utf-8')); base=ROOT/cfg['dataset_root']; out=ROOT/'data/manifests'; out.mkdir(parents=True,exist_ok=True)
 hashfile=ROOT/'reports/image_duplicates/image_hashes.csv'
 with hashfile.open(encoding='utf-8-sig',newline='') as f: hashes={Path(r['path']).as_posix():r['sha256'] for r in csv.DictReader(f)}
 fields=['split','Subject_id','Study_id','Dicom_id','image_path','ViewPosition','PatientOrientation','Rows','Columns','Predict_class']
 label_fields=['label_'+str(i) for i in range(1,11)]; summary={}; excluded=[]; patient_sets={}
 for split in ['train','valid','test']:
  with (base/(split+'.csv')).open(encoding='utf-8-sig',newline='') as f: source=list(csv.DictReader(f))
  source.sort(key=lambda r:(r['Subject_id'],r['Study_id'],r['Dicom_id']))
  manifest=[]; seen={}; studies_before={r['Study_id'] for r in source}; studies=defaultdict(list)
  for r in source:
   folder=base/split/r['Subject_id']/r['Study_id']; matches=[p for p in folder.glob(r['Dicom_id']+'.*') if p.suffix.lower() in ['.jpg','.jpeg','.png']]
   if len(matches)!=1: raise ValueError(f'Expected one image: {r}')
   path=matches[0].relative_to(ROOT).as_posix()
   if path not in hashes: raise ValueError(f'Missing hash: {path}')
   record={k:r.get(k,'') for k in fields}; record.update(split=split,image_path=path)
   if split!='test':
    labels=set(map(int,r['Predict_class'].split(';')))
    for i in range(1,11): record['label_'+str(i)]=int(i in labels)
   key=(r['Subject_id'],r['Study_id'],hashes[path])
   if split=='train' and key in seen:
    previous=seen[key]
    assert all(previous[k]==record[k] for k in label_fields)
    excluded.append({'split':split,'Subject_id':r['Subject_id'],'Study_id':r['Study_id'],'excluded_image_path':path,'retained_image_path':previous['image_path'],'sha256':hashes[path],'reason':'byte-identical duplicate within same study'}); continue
   seen[key]=record; manifest.append(record); studies[r['Study_id']].append(record)
  assert set(studies)==studies_before
  for rs in studies.values():
   if split!='test': assert len({tuple(r[k] for k in label_fields) for r in rs})==1
  selected_fields=fields+label_fields if split!='test' else [k for k in fields if k!='Predict_class']
  write(out/(split+'.csv'),[{k:r[k] for k in selected_fields} for r in manifest],selected_fields)
  patient_sets[split]={r['Subject_id'] for r in manifest}
  summary[split]={'source_images':len(source),'manifest_images':len(manifest),'excluded_images':len(source)-len(manifest),'studies':len(studies),'patients':len(patient_sets[split]),'has_labels':split!='test'}
 for a,b in [('train','valid'),('train','test'),('valid','test')]: assert not patient_sets[a]&patient_sets[b]
 write(out/'excluded_duplicates.csv',excluded,['split','Subject_id','Study_id','excluded_image_path','retained_image_path','sha256','reason'])
 result={'path_base':'project_root','label_vector_order':list(range(1,11)),'deduplication':'Train only; same patient and study and SHA-256; keep lexicographically first Dicom_id; verify labels match','splits':summary,'excluded_total':len(excluded),'validation_merged_into_training':False,'source_modified':False}
 (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (out/'README.md').write_text('''# 模型数据清单

train.csv和valid.csv每张图像一行，label_1至label_10按类别1至10排列。test.csv无标签列，禁止将未知标签作为全0处理。
image_path相对于项目根目录，代码需用项目根目录拼接，不依赖当前工作目录。
保留Subject_id和Study_id，评估和提交时必须按Study_id汇总图像预测。
训练集仅在同一患者同次检查内按SHA-256去重，每组保留Dicom_id字典序最小的图像，排除明细见excluded_duplicates.csv。原始文件不变。
验证集与测试集保持完整，验证集不得并入训练。
重建入口：scripts/data/build_manifests.py；依赖全量哈希报告reports/image_duplicates/image_hashes.csv。
''',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
