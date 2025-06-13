import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

def highlight_scene_in_glass(image):
    """
    在玻璃区域中提取景物的轮廓，并高亮显示。
    """
    # 转为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 使用Canny边缘检测找出边缘
    edges = cv2.Canny(gray, 50, 150)

    # 查找轮廓
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 创建一个新的图像用于绘制轮廓
    highlighted_image = image.copy()

    # 绘制所有轮廓
    cv2.drawContours(highlighted_image, contours, -1, (0, 255, 0), 2)  # 绿色轮廓

    return highlighted_image


