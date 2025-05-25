import os
import cv2
import numpy as np

from methods import edge_analysis,line_analysis,gradient_analysis,frequency_analysis
def crop_glass_region(image,border_ratio=0.1):
    """
    裁剪图像的中间区域，排除边框部分。
    参数：
        image: 输入图像
        border_ratio: 边框占比，例如 0.1 表示裁剪掉上下左右各 10%
    返回：
        裁剪后的中间区域图像`
    """
    h, w, _ = image.shape
    top = int(h * border_ratio)  # 裁剪顶部
    bottom = int(h * (1 - border_ratio))  # 裁剪底部
    left = int(w * border_ratio)  # 裁剪左侧
    right = int(w * (1 - border_ratio))  # 裁剪右侧

    cropped_image = image[top:bottom, left:right]
    return cropped_image

def detect_glass_flatness(image_path, glass_id, output_dir='./output'):
    """
    检测玻璃的平整性，并保存中间分析图像与结果
    Args:
        image_path: 输入原始图像路径
        glass_id: 当前玻璃的唯一编号（用于命名输出文件）
        output_dir: 保存分析中间结果的目录（默认'./output'）

    Returns:
        result_dict: 字典，含各分析图片路径、文字结论和1/0的平整性分析结果
    """
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f'Cannot read image from {image_path}')

    # Step 1: 裁剪玻璃中间区域
    cropped_image = crop_glass_region(image, border_ratio=0.1)

    # Step 2: 边缘分析
    gray = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
    edge_result, edge_analysis_txt, edge_image_path, edges = edge_analysis(
        cropped_image, gray, glass_id, output_dir
    )

    # Step 3: 直线检测分析
    line_result, line_analysis_txt, line_image_path = line_analysis(
        cropped_image, edges, glass_id, output_dir
    )

    # Step 4: 梯度分析
    gradient_result, gradient_analysis_txt, gradient_image_path = gradient_analysis(
        gray, glass_id, output_dir
    )

    # Step 5: 频域分析
    frequency_result, frequency_analysis_txt, frequency_image_path = frequency_analysis(
        gray, glass_id, output_dir
    )

    # 综合三项分析结果
    flatness_result = 1 if sum([line_result, gradient_result, frequency_result]) >= 2 else 0

    # 同步保存中间的裁剪后彩图像、灰度图像
    crop_img_path = os.path.join(output_dir, f"{glass_id}-crop.jpg")
    gray_img_path = os.path.join(output_dir, f"{glass_id}-gray.jpg")
    cv2.imwrite(crop_img_path, cropped_image)
    cv2.imwrite(gray_img_path, gray)

    # 汇总所有过程结果
    result = {
        'crop_img_path': crop_img_path,
        'gray_img_path': gray_img_path,
        'edge_image_path': edge_image_path,
        'line_image_path': line_image_path,
        'gradient_image_path': gradient_image_path,
        'frequency_image_path': frequency_image_path,

        'edge_analysis': edge_analysis_txt,
        'line_analysis': line_analysis_txt,
        'gradient_analysis': gradient_analysis_txt,
        'frequency_analysis': frequency_analysis_txt,

        'edge_result': edge_result,
        'line_result': line_result,
        'gradient_result': gradient_result,
        'frequency_result': frequency_result,
        'flatness_result': flatness_result
    }
    return result

detect_glass_flatness("test.jpg",1)