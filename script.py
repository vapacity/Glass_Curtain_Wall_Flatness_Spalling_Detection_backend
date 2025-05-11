import torch
from torchvision import transforms
from PIL import Image
import torchvision.models as models
import torch
import torch.nn as nn
import torchvision.models as models
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms
import os
# 加载模型
model = models.resnet34(pretrained=False)
num_features = model.fc.in_features
model.fc = nn.Linear(num_features, 2)  # 假设是二分类任务
model.load_state_dict(torch.load('resnet34_model.pth'))  # 加载训练好的权重
model.eval()  # 切换到评估模式

# 设备设置
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

# 图像预处理
transform = transforms.Compose([
    transforms.Resize((224, 224)),  # 调整大小
    transforms.ToTensor(),          # 转换为张量
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])  # 归一化
])

# 处理单张图片并进行分类
def classify_image(image_path):
    image = Image.open(image_path)  # 打开图片
    image = transform(image).unsqueeze(0)  # 应用预处理并增加一个批次维度
    image = image.to(device)
    
    with torch.no_grad():  # 关闭梯度计算
        outputs = model(image)
        _, predicted = torch.max(outputs, 1)  # 获取预测的类别索引
    
    class_names = ['defect', 'undefect']  # 替换为你的类别名称
    result = class_names[predicted.item()]  # 获取预测的类别名称
    return result

import cv2
import numpy as np
import os

def process_image(image_path):
    """
    Process a single image to remove cracks that are not parallel to the x-axis or y-axis
    within a ±5-degree tolerance, and draw the remaining cracks.

    Args:
        image_path (str): The path of the image to process.

    Returns:
        processed_image_path (str): The path of the saved processed image.
    """
    image = cv2.imread(image_path)
    if image is None:
        print(f"Unable to load image: {image_path}")
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    # Hough Line Transform
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=20, maxLineGap=10)
    filtered_lines = []

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi  # Calculate angle

            # Normalize angle to be between -90 and 90
            angle = (angle + 90) % 180 - 90

            # Check if the angle is within ±5 degrees of 0 (x-axis) or ±5 degrees of 90 (y-axis)
            if ((-5 <= angle <= 5) or (85 <= abs(angle) <= 95)):
                continue  # Skip lines that are not within the tolerance

            filtered_lines.append((x1, y1, x2, y2))
            cv2.line(image, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Draw line in red

    # Save the processed image
    processed_image_path = os.path.join("processed_images", os.path.basename(image_path))
    os.makedirs("processed_images", exist_ok=True)
    cv2.imwrite(processed_image_path, image)

    return processed_image_path.replace("\\", "/")

