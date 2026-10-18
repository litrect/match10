"""Check co-occurrence of No Finding (10) and disease labels (1-9)."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 config=json.loads((ROOT/'configs/project_paths.json').read_text(encoding='utf-8')); base=ROOT/config['dataset_root']; out=ROOT/'reports/label_conflicts'; out.mkdir(parents=True,exist_ok=True)
 summary={}; conflicts=[]; invalid=[]
 for split in ['train','valid']:
  with (base/(split+'.csv')).open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
  studies={}; no_finding=set(); diseases=set(); conflict_studies=set()
  for row in rows:
   try:
    tokens=row['Predict_class'].split(';'); labels=[int(x) for x in tokens]
    if not labels or len(set(labels))!=len(labels) or not set(labels)<=set(range(1,11)): raise ValueError('Empty, duplicate, or out-of-range labels')
   except (ValueError,KeyError) as e:
    invalid.append(dict(split=split,**row,error=str(e))); continue
   key=(row['Subject_id'],row['Study_id']); studies.setdefault(key,[]).append(set(labels))
   if 10 in labels: no_finding.add(key)
   if set(labels)&set(range(1,10)): diseases.add(key)
   if 10 in labels and len(labels)>1:
    conflicts.append(dict(split=split,**row,conflict_type='No Finding co-occurs with disease')); conflict_studies.add(key)
  inconsistent=[key for key,sets in studies.items() if any(x!=sets[0] for x in sets[1:])]
  summary[split]={'image_records':len(rows),'study_count':len(studies),'no_finding_studies':len(no_finding),'disease_studies':len(diseases),'conflicting_image_records':sum(r['split']==split for r in conflicts),'conflicting_studies':len(conflict_studies),'inconsistent_study_labels':len(inconsistent),'invalid_label_rows':sum(r['split']==split for r in invalid)}
 for name,records in [('conflicts',conflicts),('invalid_labels',invalid)]:
  fields=['split','Dicom_id','Subject_id','Study_id','Predict_class']+(['conflict_type'] if name=='conflicts' else ['error'])
  with (out/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(records)
 result={'rule':'Class 10 (No Finding) co-occurring with any class 1-9 is flagged for review','splits':summary,'total_conflict_studies':sum(x['conflicting_studies'] for x in summary.values()),'total_invalid_label_rows':len(invalid),'test_split':'Not checked because test labels are not provided','source_data_modified':False}
 (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 lines=['# 无异常发现标签共现检查','', '检查类别10是否与类别1至9同时标注，仅记录异常，不修改数据。','', '| 集合 | 检查数 | 仅类别10检查数 | 含疾病检查数 | 冲突检查数 |','|---|---:|---:|---:|---:|']
 for split,s in summary.items(): lines.append(f"| {split} | {s['study_count']} | {s['no_finding_studies']-s['conflicting_studies']} | {s['disease_studies']} | {s['conflicting_studies']} |")
 lines+=['',f"冲突检查总数：{result['total_conflict_studies']}。非法标签记录：{len(invalid)}。",'','同次检查的多图标签一致性亦已核对；测试集无标签，不纳入检查。','此检查仅验证标注逻辑，不代表医学标注已被临床验证。']
 (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
