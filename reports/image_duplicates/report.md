# 重复图像检查报告

方法：对完整文件字节计算SHA-256，仅识别内容完全相同的文件。

- 图像总数：33984
- 成功计算：33984
- 读取失败：0
- 重复组数：14
- 涉及图像：28
- 多余副本数：14
- 跨数据集重复组数：0
- 跨集合组合统计：{}
- 集合内部重复组数：{'train': 14}
- 耗时：96.1秒

逐图哈希见image_hashes.csv，重复组见duplicate_groups.csv，读取异常见hash_errors.csv。
本检查未删除或移动原始文件，不覆盖重编码、缩放或视觉相似图像。

## 重复图像标签核对

- same_patient_groups: 14
- same_study_groups: 14
- consistent_label_groups: 14

患者、检查及标签明细见duplicate_details.csv。
