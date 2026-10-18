"""Read-only full image integrity audit. Run from any working directory."""
import csv,json,time,warnings
from pathlib import Path
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from PIL import Image,ImageFile
ROOT=Path(__file__).resolve().parents[2]
CFG=json.loads((ROOT/'configs/project_paths.json').read_text(encoding='utf-8'))
BASE=ROOT/CFG['dataset_root']; OUT=ROOT/'reports/image_integrity'; OUT.mkdir(parents=True,exist_ok=True)
ImageFile.LOAD_TRUNCATED_IMAGES=False

def check(job):
 split,path,rows=job
 errors=[]; width=height=None; fmt=mode=''
 if path.stat().st_size==0: errors.append(('empty_file','0 bytes'))
 try:
  with Image.open(path) as im:
   width,height=im.size; fmt=im.format; mode=im.mode; im.verify()
  with Image.open(path) as im: im.load()
  if fmt not in ('JPEG','PNG'): errors.append(('unexpected_format',str(fmt)))
 except Exception as e: errors.append(('decode_error',f'{type(e).__name__}: {e}'))
 for row in rows:
  try:
   expected=(int(row['Columns']),int(row['Rows']))
   if width is not None and (width,height)!=expected: errors.append(('dimension_mismatch',f'CSV={expected}; actual={(width,height)}'))
  except Exception as e: errors.append(('invalid_csv_dimensions',str(e)))
 return {'split':split,'path':str(path),'width':width,'height':height,'format':fmt,'mode':mode,'errors':errors,'referenced':bool(rows)}

def main():
 start=time.time(); issues=[]; summaries={}; jobs=[]
 for split in ['train','valid','test']:
  with (BASE/(split+'.csv')).open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
  files=[p for p in (BASE/split).rglob('*') if p.is_file()]
  images=[p for p in files if p.suffix.lower() in ['.jpg','.jpeg','.png']]
  by_key=defaultdict(list)
  for p in images: by_key[(p.parent.parent.name,p.parent.name,p.stem)].append(p)
  refs=defaultdict(list); seen=Counter()
  for row in rows:
   key=(row['Subject_id'],row['Study_id'],row['Dicom_id']); seen[key]+=1; matches=by_key.get(key,[])
   if not matches: issues.append(dict(split=split,path='/'.join(key),issue='missing_file',detail='CSV record has no image'))
   if len(matches)>1: issues.append(dict(split=split,path='/'.join(key),issue='multiple_matches',detail=str(len(matches))))
   for p in matches: refs[p].append(row)
  for key,n in seen.items():
   if n>1: issues.append(dict(split=split,path='/'.join(key),issue='duplicate_csv_record',detail=str(n)))
  for p in images:
   if p not in refs: issues.append(dict(split=split,path=str(p),issue='unreferenced_image',detail='Image absent from CSV'))
   jobs.append((split,p,refs.get(p,[])))
  summaries[split]={'csv_records':len(rows),'image_files':len(images),'other_files':len(files)-len(images),'checked':0,'passed':0,'failed':0,'formats':Counter(),'modes':Counter()}
 total=len(jobs); print(f'Indexed {total} images; decoding with 4 workers',flush=True)
 with (OUT/'image_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=['split','path','width','height','format','mode','referenced','status','detail']); writer.writeheader()
  with ThreadPoolExecutor(max_workers=4) as pool:
   futures=[pool.submit(check,j) for j in jobs]
   for n,future in enumerate(as_completed(futures),1):
    r=future.result(); s=summaries[r['split']]; s['checked']+=1; s['failed' if r['errors'] else 'passed']+=1; s['formats'][r['format']]+=1; s['modes'][r['mode']]+=1
    for code,msg in r['errors']: issues.append(dict(split=r['split'],path=r['path'],issue=code,detail=msg))
    record={k:v for k,v in r.items() if k!='errors'}; record.update(status='FAIL' if r['errors'] else 'PASS',detail=' | '.join(code+': '+msg for code,msg in r['errors'])); writer.writerow(record)
    if n%500==0 or n==total: print(f'Progress {n}/{total}; elapsed {time.time()-start:.0f}s',flush=True); f.flush()
 with (OUT/'issues.csv').open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=['split','path','issue','detail']); writer.writeheader(); writer.writerows(issues)
 result={'dataset_root':str(BASE),'checks':['CSV image correspondence','missing and extra images','duplicate CSV records','nonempty files','Pillow verify and full decode with truncated images disallowed','actual dimensions versus CSV','JPEG or PNG format'],'splits':summaries,'total_images':total,'issue_count':len(issues),'issues_by_type':dict(Counter(x['issue'] for x in issues)),'elapsed_seconds':round(time.time()-start,1),'scope_note':'File integrity only; no medical label review or image-content duplication hashing.'}
 (OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 lines=['# 全量图像完整性检查报告','',f'共检查 {total} 张图像；异常记录 {len(issues)} 条。','', '| 数据集 | CSV记录 | 图像文件 | 通过 | 失败 |','|---|---:|---:|---:|---:|']
 for split,s in summaries.items(): lines.append(f"| {split} | {s['csv_records']} | {s['image_files']} | {s['passed']} | {s['failed']} |")
 lines+=['','检查范围：CSV与图像对应、缺失及额外图像、重复CSV记录、空文件、格式验证、严格完整解码、实际尺寸与CSV比对。','', '本检查不判断医学标签是否正确，也不包含图像内容哈希去重。','',f"耗时 {result['elapsed_seconds']} 秒。详细结果见 image_results.csv，异常见 issues.csv。"]
 (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__': main()
