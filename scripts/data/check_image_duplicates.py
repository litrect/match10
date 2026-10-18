"""Find byte-identical images using SHA-256 without changing source files."""
import csv,json,hashlib,time
from pathlib import Path
from collections import defaultdict,Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[2]

def digest(item):
 split,path=item; h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
 return {'split':split,'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':h.hexdigest()}

def main():
 start=time.time(); config=json.loads((ROOT/'configs/project_paths.json').read_text(encoding='utf-8')); base=ROOT/config['dataset_root']; out=ROOT/'reports/image_duplicates'; out.mkdir(parents=True,exist_ok=True)
 items=[(s,p) for s in ['train','valid','test'] for p in (base/s).rglob('*') if p.is_file() and p.suffix.lower() in ['.jpg','.jpeg','.png']]
 groups=defaultdict(list); errors=[]
 print(f'Indexed {len(items)} images',flush=True)
 with (out/'image_hashes.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['split','path','bytes','sha256']); w.writeheader()
  with ThreadPoolExecutor(max_workers=4) as pool:
   tasks={pool.submit(digest,item):item for item in items}
   for n,future in enumerate(as_completed(tasks),1):
    try:
     r=future.result(); w.writerow(r); groups[r['sha256']].append(r)
    except Exception as e:
     split,path=tasks[future]; errors.append({'split':split,'path':str(path.relative_to(ROOT)),'error':f'{type(e).__name__}: {e}'})
    if n%2000==0 or n==len(items): f.flush(); print(f'Hashed {n}/{len(items)}; elapsed {time.time()-start:.0f}s',flush=True)
 duplicates=[(h,rs) for h,rs in groups.items() if len(rs)>1]; cross=[]; within=Counter(); pair_counts=Counter(); rows=[]
 for gid,(h,rs) in enumerate(sorted(duplicates),1):
  splits=sorted({r['split'] for r in rs}); kind='cross_split' if len(splits)>1 else 'within_split'
  if len(splits)>1:
   cross.append(h)
   for i,a in enumerate(splits):
    for b in splits[i+1:]: pair_counts[a+'__'+b]+=1
  for s,n in Counter(r['split'] for r in rs).items():
   if n>1: within[s]+=1
  for r in rs: rows.append(dict(group_id=gid,group_type=kind,group_size=len(rs),**r))
 with (out/'duplicate_groups.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['group_id','group_type','group_size','split','path','bytes','sha256']); w.writeheader(); w.writerows(rows)
 with (out/'hash_errors.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['split','path','error']); w.writeheader(); w.writerows(errors)
 summary={'method':'SHA-256 of complete file bytes','total_images':len(items),'hashed_images':sum(len(v) for v in groups.values()),'hash_errors':len(errors),'unique_hashes':len(groups),'duplicate_groups':len(duplicates),'images_in_duplicate_groups':len(rows),'redundant_copies':sum(len(rs)-1 for _,rs in duplicates),'cross_split_duplicate_groups':len(cross),'cross_split_pairs_group_counts':dict(pair_counts),'within_split_duplicate_groups':dict(within),'elapsed_seconds':round(time.time()-start,1),'scope_note':'Detects byte-identical files only, not re-encoded, resized, or visually similar images. No original files changed.'}
 (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 text=f'''# 重复图像检查报告

方法：对完整文件字节计算SHA-256，仅识别内容完全相同的文件。

- 图像总数：{len(items)}
- 成功计算：{summary['hashed_images']}
- 读取失败：{len(errors)}
- 重复组数：{len(duplicates)}
- 涉及图像：{len(rows)}
- 多余副本数：{summary['redundant_copies']}
- 跨数据集重复组数：{len(cross)}
- 跨集合组合统计：{dict(pair_counts)}
- 集合内部重复组数：{dict(within)}
- 耗时：{summary['elapsed_seconds']}秒

逐图哈希见image_hashes.csv，重复组见duplicate_groups.csv，读取异常见hash_errors.csv。
本检查未删除或移动原始文件，不覆盖重编码、缩放或视觉相似图像。
'''
 (out/'report.md').write_text(text,encoding='utf-8'); print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__': main()
