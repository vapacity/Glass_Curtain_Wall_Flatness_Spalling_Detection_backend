import os
import json
import shutil
import numpy as np
from sklearn.model_selection import train_test_split
from collections import defaultdict
from datetime import datetime

def load_annotations(annotation_path):
    """加载并预处理标注数据"""
    with open(annotation_path) as f:
        data = json.load(f)
    
    # 添加派生特征
    for img in data['images']:
        # 解析采集日期
        img['year'] = datetime.strptime(img['date'], "%Y-%m-%d").year
        # 生成分层键：工程类型+区域+年份
        img['stratify_key'] = f"{img['project_type']}-{img['region']}-{img['year']}"
        # 生成样本权重：裂纹样本加权
        img['sample_weight'] = 3.0 if any(ann['type'] == 'crack' for ann in img['annotations']) else 1.0
    
    return data

def create_split_folders(output_root):
    """创建标准目录结构"""
    splits = ['train', 'val', 'test']
    for split in splits:
        os.makedirs(os.path.join(output_root, split, 'images'), exist_ok=True)
        os.makedirs(os.path.join(output_root, split, 'labels'), exist_ok=True)
    return os.path.join(output_root, 'meta')

def stratified_split(data, config):
    """执行分层划分"""
    # 收集分层键和样本索引
    stratify_keys = [img['stratify_key'] for img in data['images']]
    indices = np.arange(len(data['images']))
    sample_weights = [img['sample_weight'] for img in data['images']]

    # 第一阶段：训练+临时 与 测试集划分
    train_temp_idx, test_idx = train_test_split(
        indices,
        test_size=config['test_ratio'],
        stratify=stratify_keys,
        random_state=config['seed'],
        shuffle=True
    )

    # 第二阶段：训练集与验证集划分
    train_idx, val_idx = train_test_split(
        train_temp_idx,
        test_size=config['val_ratio']/(1-config['test_ratio']),
        stratify=[stratify_keys[i] for i in train_temp_idx],
        random_state=config['seed'],
        shuffle=True
    )

    return train_idx, val_idx, test_idx

def distribute_files(data, indices, split_name, output_root):
    """分发文件到目标目录并生成元数据"""
    meta = []
    for idx in indices:
        img_info = data['images'][idx]
        
        # 复制图像文件
        src_img = os.path.join(config['image_dir'], img_info['file_name'])
        dst_img = os.path.join(output_root, split_name, 'images', img_info['file_name'])
        shutil.copy(src_img, dst_img)
        
        # 生成标注文件
        anno_path = os.path.join(output_root, split_name, 'labels', 
                               f"{os.path.splitext(img_info['file_name'])[0]}.json")
        with open(anno_path, 'w') as f:
            json.dump(img_info, f)
        
        # 记录元数据
        meta.append({
            'file_name': img_info['file_name'],
            'split': split_name,
            'project_type': img_info['project_type'],
            'region': img_info['region'],
            'date': img_info['date']
        })
    
    return meta

def generate_statistics(data, splits):
    """生成划分统计报告"""
    stats = defaultdict(lambda: defaultdict(int))
    
    for split, indices in splits.items():
        for idx in indices:
            img = data['images'][idx]
            key = (img['project_type'], img['region'], img['year'])
            stats[key][split] += 1
            if any(ann['type'] == 'crack' for ann in img['annotations']):
                stats['class_dist'][f'{split}_crack'] += 1
            else:
                stats['class_dist'][f'{split}_normal'] += 1
    
    return stats

def main_split(config):
    """主划分函数"""
    # 加载并预处理数据
    data = load_annotations(config['annotation_path'])
    
    # 创建目录结构
    meta_dir = create_split_folders(config['output_dir'])
    
    # 执行分层划分
    train_idx, val_idx, test_idx = stratified_split(data, config)
    splits = {
        'train': train_idx,
        'val': val_idx,
        'test': test_idx
    }
    
    # 分发文件并收集元数据
    all_meta = []
    for split_name, indices in splits.items():
        meta = distribute_files(data, indices, split_name, config['output_dir'])
        all_meta.extend(meta)
    
    # 保存元数据
    with open(os.path.join(meta_dir, 'metadata.json'), 'w') as f:
        json.dump(all_meta, f, indent=2)
    
    # 生成统计报告
    stats = generate_statistics(data, splits)
    with open(os.path.join(meta_dir, 'statistics.json'), 'w') as f:
        json.dump(stats, f, indent=2)
    
    print("数据集划分完成")
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    # 配置参数
    dataset_dir="F:/GlassDetection/dataset2"
    save_dir = "F:/GlassDetection/dataset"
    config = {
    'image_dir': dataset_dir,  # 原始数据路径
    'annotation_path': (dataset_dir+"/annotations.json"),  # 标注文件路径
    'output_dir': save_dir,   # 划分后输出路径
    'invalid_dir': (save_dir+"/invalid_data"),  # 无效数据存放路径
    'test_ratio': 0.15,    # 测试集比例
    'val_ratio': 0.15,     # 验证集比例
    'seed': 42,            # 随机种子
    'stratify_by': ['project_type', 'region', 'year']  # 分层抽样依据
}
    
    # 执行划分
    main_split(config)