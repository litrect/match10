"""Describe class, co-occurrence, image count and view distributions."""
import csv,json
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[2]
def write_csv(path,rows,fields):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def main():
 cfg=json.loads((ROOT/'configs/project_paths.json').read_text(encoding='utf-8')); base=ROOT/cfg['dataset_root']; out=ROOT/'reports/data_distribution'; out.mkdir(parents=True,exist_ok=True)
 mapping=json.loads((ROOT/cfg['class_mapping']).read_text(encoding='utf-8'))['classes']; names={r['class_id']:r['name_zh'] for r in mapping}
 stats={}; class_rows=[]; pair_rows=[]; count_rows=[]; view_rows=[]; combo_rows=[]
 for split in ['train','valid','test']:
  with (base/(split+'.csv')).open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
  studies=defaultdict(list)
  for r in rows: studies[r['Study_id']].append(r)
  image_counts=Counter(len(rs) for rs in studies.values()); views=Counter(r['ViewPosition'] or '(missing)' for r in rows)
  orientations=Counter(r['PatientOrientation'] or '(missing)' for r in rows)
  stats[split]={'images':len(rows),'studies':len(studies),'patients':len({r['Subject_id'] for r in rows}),'images_per_study':dict(sorted(image_counts.items())),'view_image_counts':dict(views),'patient_orientation_image_counts':dict(orientations)}
  for n,c in sorted(image_counts.items()): count_rows.append(dict(split=split,images_per_study=n,study_count=c,percent=round(100*c/len(studies),4)))
  view_studies=Counter()
  for rs in studies.values(): view_studies.update({r['ViewPosition'] or '(missing)' for r in rs})
  for v,c in views.most_common(): view_rows.append(dict(split=split,view=v,image_count=c,image_percent=round(100*c/len(rows),4),study_count=view_studies[v],study_percent=round(100*view_studies[v]/len(studies),4)))
  if split=='test': continue
  labels=[]
  for sid,rs in studies.items():
   sets=[tuple(sorted(map(int,r['Predict_class'].split(';')))) for r in rs]
   if len(set(sets))!=1: raise ValueError('Inconsistent study labels')
   labels.append(sets[0])
  counts=Counter(c for ls in labels for c in ls); cardinality=Counter(map(len,labels)); combos=Counter(labels)
  stats[split]['label_count_per_study']=dict(sorted(cardinality.items())); stats[split]['multi_label_studies']=sum(c for n,c in cardinality.items() if n>1)
  for i in range(1,11): class_rows.append(dict(split=split,class_id=i,name_zh=names[i],positive_studies=counts[i],negative_studies=len(studies)-counts[i],positive_percent=round(100*counts[i]/len(studies),4)))
  for i in range(1,11):
   for j in range(i,11):
    n=sum(i in ls and j in ls for ls in labels); pair_rows.append(dict(split=split,class_id_a=i,class_name_a=names[i],class_id_b=j,class_name_b=names[j],study_count=n,percent=round(100*n/len(studies),4)))
  for ls,c in combos.most_common(): combo_rows.append(dict(split=split,labels=';'.join(map(str,ls)),names=';'.join(names[x] for x in ls),study_count=c,percent=round(100*c/len(studies),4)))
 for filename,rs in [('class_frequency',class_rows),('label_cooccurrence',pair_rows),('images_per_study',count_rows),('view_distribution',view_rows),('label_combinations',combo_rows)]: write_csv(out/(filename+'.csv'),rs,list(rs[0]))
 comparisons=[]
 for i in range(1,11):
  a=next(r for r in class_rows if r['split']=='train' and r['class_id']==i); b=next(r for r in class_rows if r['split']=='valid' and r['class_id']==i)
  comparisons.append(dict(class_id=i,name_zh=names[i],train_positive=a['positive_studies'],train_percent=a['positive_percent'],valid_positive=b['positive_studies'],valid_percent=b['positive_percent'],valid_minus_train_percentage_points=round(b['positive_percent']-a['positive_percent'],4)))
 write_csv(out/'train_valid_comparison.csv',comparisons,list(comparisons[0]))
 (out/'summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 lines=['# 数据分布分析报告','','类别与共现按Study_id统计，每次检查只计一次。视角按图像统计，同时提供包含该视角的检查数；一项检查可能包含多种视角。原始数据未修改。','','## 训练与验证类别分布','','| 编号 | 类别 | 训练阳性检查 | 占比 | 验证阳性检查 | 占比 | 验证减训练百分点 |','|---|---|---:|---:|---:|---:|---:|']
 for r in comparisons: lines.append(f"| {r['class_id']} | {r['name_zh']} | {r['train_positive']} | {r['train_percent']:.2f}% | {r['valid_positive']} | {r['valid_percent']:.2f}% | {r['valid_minus_train_percentage_points']:+.2f} |")
 lines+=['','## 多标签与图像组成','']
 for split,s in stats.items():
  lines.append(f"- {split}：{s['patients']}名患者，{s['studies']}次检查，{s['images']}张图像；每次检查图像数分布：{s['images_per_study']}。")
  lines.append(f"  图像视角分布：{s['view_image_counts']}。")
  if 'label_count_per_study' in s: lines.append(f"  每次检查标签数量分布：{s['label_count_per_study']}；多标签检查{s['multi_label_studies']}次，占{100*s['multi_label_studies']/s['studies']:.2f}%。")
 lines+=['','## 常见疾病标签共现','']
 for split in ['train','valid']:
  pairs=sorted([r for r in pair_rows if r['split']==split and r['class_id_a']!=r['class_id_b']],key=lambda x:x['study_count'],reverse=True)[:5]
  lines.append(f'- {split}前五组：'+'；'.join(f"{r['class_name_a']}与{r['class_name_b']} {r['study_count']}次" for r in pairs)+'。')
 lines+=['','## 对训练的建议','','- 验证集保持独立，不并入训练。按检查级Macro-AUC评估，同时记录每类AUC。','- 各类别不均衡，先建立普通BCE基线，再以验证集结果决定是否采用类别加权或采样。','- 少数类别的验证阳性检查数较少，应关注指标波动，不凭单次小幅提升决定方案。','- 多图检查需在推理时汇总为检查级预测；训练清单可以排除已识别的14个重复副本，原始文件保持不变。','- 视角和图像数量存在差异，数据读取必须支持不同检查的图像数；当前统计为原始记录，尚未去重。','','详见同目录CSV文件；测试集无标签，仅统计图像和视角。']
 (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps({'stats':stats,'comparison':comparisons,'top_train_pairs':sorted([r for r in pair_rows if r['split']=='train' and r['class_id_a']!=r['class_id_b']],key=lambda x:x['study_count'],reverse=True)[:5]},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
