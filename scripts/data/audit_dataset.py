import csv,random,json
from pathlib import Path
from collections import defaultdict,Counter
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
base = ROOT / 'dataset'
out = ROOT / 'reports' / 'dataset_audit'
out.mkdir(parents=True, exist_ok=True)
data={s:list(csv.DictReader((base/(s+'.csv')).open(encoding='utf-8-sig'))) for s in ['train','valid','test']}
patients=sorted({r['Subject_id'] for r in data['train']}); selected=sorted(random.Random(20261018).sample(patients,10))
summary={}; issues=[]
for split,rows in data.items():
 studies=defaultdict(list); counts=Counter(); bad=[]
 for r in rows:
  studies[r['Study_id']].append(r)
  if 'Predict_class' in r:
   try:
    ids=[int(x) for x in r['Predict_class'].split(';')]
    if len(ids)!=len(set(ids)) or not set(ids)<=set(range(1,11)): bad.append(r)
   except ValueError: bad.append(r)
 for sid,rs in studies.items():
  if len({r['Subject_id'] for r in rs})>1: issues.append([split,sid,'multiple patients'])
  if 'Predict_class' in rs[0]:
   labs={tuple(sorted(map(int,r['Predict_class'].split(';')))) for r in rs}
   if len(labs)>1: issues.append([split,sid,'inconsistent labels'])
   counts.update(set(int(x) for x in rs[0]['Predict_class'].split(';')))
 summary[split]={'images':len(rows),'patients':len({r['Subject_id'] for r in rows}),'studies':len(studies),'invalid_label_rows':len(bad),'class_counts_per_study':dict(sorted(counts.items()))}
summary['patient_overlap']={a+'_'+b:len({r['Subject_id'] for r in data[a]}&{r['Subject_id'] for r in data[b]}) for a,b in [('train','valid'),('train','test'),('valid','test')]}
sample=[]; details=[]
for pid in selected:
 rows=[r for r in data['train'] if r['Subject_id']==pid]; failures=[]
 for r in rows:
  folder=base/'train'/pid/r['Study_id']; files=list(folder.glob(r['Dicom_id']+'.*'))
  status='ok'
  try:
   if len(files)!=1: raise ValueError('missing or multiple files')
   with Image.open(files[0]) as im:
    size=im.size; im.load()
   if size!=(int(r['Columns']),int(r['Rows'])): raise ValueError('size mismatch')
  except Exception as e: status=str(e); failures.append(status)
  details.append(dict(r,Image_path=str(files[0].resolve()) if files else '',Image_check=status))
 studies=sorted({r['Study_id'] for r in rows}); labs=sorted({int(x) for r in rows for x in r['Predict_class'].split(';')})
 sample.append({'Subject_id':pid,'Study_count':len(studies),'Image_count':len(rows),'Class_ids':';'.join(map(str,labs)),'Checks':'PASS' if not failures else ';'.join(failures),'Study_labels':' | '.join(s+':'+next(r['Predict_class'] for r in rows if r['Study_id']==s) for s in studies)})
for name,rows in [('sample_10_patients',sample),('sample_image_details',details)]:
 with (out/(name+'.csv')).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
summary['metadata_issues']=issues
(out/'audit_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'summary':summary,'sample':sample},ensure_ascii=False,indent=2))
