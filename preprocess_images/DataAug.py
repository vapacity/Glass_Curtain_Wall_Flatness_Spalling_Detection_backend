import cv2
import numpy as np
from albumentations import (
    Compose, Rotate, HorizontalFlip, RandomScale, 
    RandomBrightnessContrast, GaussNoise, SaltAndPepperNoise,
    Perspective
)

def image_augmentation(image_path, save_dir, p=1.0):
    """
    对输入图像进行数据增强
    Args:
        image_path: 输入图像路径
        save_dir: 增强后图像保存目录
        p: 增强操作概率（默认1.0全应用）
    """
    # 读取图像
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # 转换为RGB格式
    
    # 定义增强策略
    transform = Compose([
        Rotate(limit=15, p=0.5),                  # 旋转±15度（50%概率）
        HorizontalFlip(p=0.5),                   # 水平翻转（50%概率）
        RandomScale(scale_limit=(0.2, 0.2), p=0.5),  # 缩放0.8-1.2倍（50%概率）
        RandomBrightnessContrast(
            brightness_limit=0.2, 
            contrast_limit=0.15, 
            p=0.5
        ),                                       # 亮度±20%/对比度±15%（50%概率）
        GaussNoise(var_limit=(10, 50), p=0.3),   # 高斯噪声（σ=0.1~0.3，30%概率）
        SaltAndPepperNoise(p=0.1),               # 椒盐噪声（密度0.03，10%概率）
        Perspective(p=0.2)                       # 透视畸变（20%概率）
    ], p=p)

    # 应用增强
    augmented = transform(image=image)
    
    # 保存增强图像
    filename = image_path.split('/')[-1]
    save_path = f"{save_dir}/{filename}"
    cv2.imwrite(save_path, augmented['image'])


if __name__ == "__main__":
    import os
    from glob import glob
    
    # 设置参数
    dataset_dir = "F:/GlassDetection/dataset1"
    save_dir = "F:/GlassDetection/dataset2"
    os.makedirs(save_dir, exist_ok=True)
    
    # 获取所有图像路径
    image_paths = glob(f"{dataset_dir}/*.jpg") + glob(f"{dataset_dir}/*.png")
    
    # 批量增强
    for img_path in image_paths:
        image_augmentation(img_path, save_dir, p=1.0)