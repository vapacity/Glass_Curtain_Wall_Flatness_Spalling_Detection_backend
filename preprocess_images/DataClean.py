import os
import json
import hashlib
from PIL import Image
from PIL import ImageFile
import shutil
import piexif

# 允许加载大图以防止文件截断错误
ImageFile.LOAD_TRUNCATED_IMAGES = True

def validate_image_integrity(file_path):
    """验证图像文件的完整性"""
    try:
        with Image.open(file_path) as img:
            img.verify()  # 基础验证
            img.load()    # 强制加载所有像素数据
        return True
    except (IOError, SyntaxError) as e:
        return False

def get_image_metadata(file_path):
    """获取图像元数据，包含EXIF信息"""
    try:
        exif_dict = piexif.load(file_path)
        return exif_dict
    except Exception as e:
        return None

def calculate_md5(file_path):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def check_shooting_angle(metadata):
    """通过EXIF信息分析拍摄角度"""
    if metadata:
        try:
            # 从EXIF标签获取方向信息（不同相机可能使用不同标签）
            orientation = metadata["0th"].get(piexif.ImageIFD.Orientation, 1)
            angle_map = {3: 180, 6: 90, 8: 270}
            return angle_map.get(orientation, 0)
        except KeyError:
            pass
    return 0  # 默认角度为0

def clean_dataset(config):
    """主清洗函数"""
    # 创建输出目录结构
    os.makedirs(config['output_dir'], exist_ok=True)
    os.makedirs(config['invalid_dir'], exist_ok=True)
    
    # 初始化数据记录
    validation_report = {
        'valid_count': 0,
        'invalid_records': [],
        'md5_checksums': {}
    }

    # 加载标注数据
    with open(config['annotation_path']) as f:
        annotations = json.load(f)['images']

    # 创建标注查找字典
    annotation_lookup = {img['file_name']: img for img in annotations}

    # 遍历处理每张图片
    for filename in os.listdir(config['image_dir']):
        file_path = os.path.join(config['image_dir'], filename)
        dest_path = os.path.join(config['output_dir'], filename)
        invalid_reasons = []

        # 1. 基础文件验证
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            invalid_reasons.append('Invalid file format')
        else:
            # 2. 计算文件哈希值
            file_hash = calculate_md5(file_path)
            if file_hash in validation_report['md5_checksums']:
                invalid_reasons.append('Duplicate file')
            validation_report['md5_checksums'][file_hash] = filename

            # 3. 图像完整性验证
            if not validate_image_integrity(file_path):
                invalid_reasons.append('Corrupted image file')

            # 4. 获取图像元数据
            metadata = get_image_metadata(file_path)
            shooting_angle = check_shooting_angle(metadata)

            # 5. 图像尺寸验证
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
                    if min(width, height) < 224:
                        invalid_reasons.append(f'Insufficient resolution ({width}x{height})')
            except Exception as e:
                invalid_reasons.append('Unreadable image dimensions')

            # 6. 标注数据验证
            annotation = annotation_lookup.get(filename)
            if not annotation:
                invalid_reasons.append('Missing annotation')
            else:
                # 裂纹标注验证
                for ann in annotation.get('annotations', []):
                    if ann['type'] == 'crack':
                        crack_length = ann['length']
                        max_allowed = annotation['width'] * 0.2
                        if crack_length > max_allowed:
                            invalid_reasons.append(f'Crack length exceeds limit ({crack_length}px)')

                # 平整度一致性验证
                flatness = annotation.get('flatness_score')
                curvature = annotation.get('curvature')
                if curvature > 0.1 and flatness > 0.5:
                    invalid_reasons.append('Flatness-curvature mismatch')

                # 拍摄角度验证
                if not (-30 <= shooting_angle <= 30):
                    invalid_reasons.append(f'Invalid shooting angle ({shooting_angle}°)')

        # 处理验证结果
        if invalid_reasons:
            # 记录无效文件信息
            record = {
                'filename': filename,
                'reasons': invalid_reasons,
                'hash': file_hash,
                'metadata': str(metadata)
            }
            validation_report['invalid_records'].append(record)
            
            # 移动无效文件
            shutil.move(file_path, os.path.join(config['invalid_dir'], filename))
        else:
            # 复制有效文件并更新标注
            shutil.copy(file_path, dest_path)
            validation_report['valid_count'] += 1

    # 保存清洗报告
    with open(os.path.join(config['output_dir'], 'validation_report.json'), 'w') as f:
        json.dump(validation_report, f, indent=2)

    print(f"清洗完成 - 有效图片: {validation_report['valid_count']}")
    print(f"无效图片: {len(validation_report['invalid_records'])}")
    return validation_report

# 配置参数
dataset_dir="F:/GlassDetection/dataset0"
save_dir = "F:/GlassDetection/dataset1"
config = {
    'image_dir': dataset_dir,  
    'annotation_path': os.path.join(dataset_dir, 'annotations.json'),
    'output_dir': os.path.join(save_dir, 'cleaned_data'),
    'invalid_dir': os.path.join(save_dir, 'invalid_data')
}

# 执行清洗流程
clean_dataset(config)