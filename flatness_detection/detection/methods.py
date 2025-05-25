import os
import cv2
import numpy as np
import matplotlib.pyplot as plt

def edge_analysis(cropped_image, gray, glass_id, output_dir='./output'):
    """
    对裁剪后的图像进行边缘检测与清晰度分析
    Args:
        cropped_image: 裁剪得到的BGR彩图像（numpy ndarray）
        gray: 裁剪区域对应的灰度图像（numpy ndarray）
        glass_id: 当前玻璃的唯一标识（用于命名输出文件）
        output_dir: 结果保存目录（默认'./output'）
    Returns:
        edge_result: 边缘分析结果，0代表不平整，1代表平整
        edge_analysis_text: 分析结论的文字描述
        edge_image_path: 边缘检测结果图片的保存路径
        edges: 边缘二值图像（numpy ndarray）
    """
    edges = cv2.Canny(gray, 50, 150)
    edge_image_path = os.path.join(output_dir, f"{glass_id}-edges.jpg")
    cv2.imwrite(edge_image_path, edges)
    edge_count = np.sum(edges > 0)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    laplacian_variance = laplacian.var()
    if laplacian_variance < 10:
        edge_result = 0
        edge_analysis_text = f"玻璃表面可能不平整（边缘模糊，拉普拉斯方差：{laplacian_variance:.2f}）"
    elif edge_count < 500:
        edge_result = 1
        edge_analysis_text = f"玻璃表面平整（边缘正常，但简单背景，边缘数量：{edge_count}）"
    else:
        edge_result = 1
        edge_analysis_text = f"玻璃表面平整（边缘清晰且正常，拉普拉斯方差：{laplacian_variance:.2f}，边缘数量：{edge_count}）"
    return edge_result, edge_analysis_text, edge_image_path, edges

def line_analysis(cropped_image, edges, glass_id, output_dir='./output'):
    """
    对边缘检测结果做直线检测，并分析角度变化
    Args:
        cropped_image: 裁剪后的原始BGR图像（numpy ndarray）
        edges: 边缘二值化图像（numpy ndarray）
        glass_id: 当前玻璃的唯一标识（用于命名输出文件）
        output_dir: 结果保存目录（默认'./output'）
    Returns:
        line_result: 直线检测分析结果，0代表不平整，1代表平整
        line_analysis_text: 分析结论的文字描述
        line_image_path: 检测并绘制直线后的图片保存路径
    """
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=10)
    line_image = cropped_image.copy()
    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(line_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            angles.append(angle)
    line_image_path = os.path.join(output_dir, f"{glass_id}-lines.jpg")
    cv2.imwrite(line_image_path, line_image)
    num_lines = len(lines) if lines is not None else 0
    angle_std = np.std(angles) if angles else 0.0
    line_result = 1 if angle_std < 50 else 0
    if line_result == 0:
        line_analysis_text = f"玻璃表面可能不平整（角度标准差较大: {angle_std:.2f}）"
    else:
        line_analysis_text = "玻璃表面平整（直线角度正常）"
    return line_result, line_analysis_text, line_image_path

def gradient_analysis(gray, glass_id, output_dir='./output'):
    """
    对图像灰度梯度进行分析，评价玻璃表面变化状况
    Args:
        gray: 灰度图像（numpy ndarray）
        glass_id: 当前玻璃的唯一标识（用于命名输出文件）
        output_dir: 结果保存目录（默认'./output'）
    Returns:
        gradient_result: 梯度分析结果，0代表不平整，1代表平整
        gradient_analysis_text: 分析结论的文字描述
        gradient_image_path: 梯度幅值图像的保存路径
    """
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    grad_magnitude = cv2.magnitude(grad_x, grad_y)
    gradient_image_path = os.path.join(output_dir, f"{glass_id}-gradient.jpg")
    cv2.imwrite(gradient_image_path, np.uint8(grad_magnitude))
    gradient_mean = np.mean(grad_magnitude)
    gradient_std = np.std(grad_magnitude)
    gradient_result = 1 if gradient_std < 100 else 0
    if gradient_result == 0:
        gradient_analysis_text = f"玻璃表面可能不平整（梯度标准差较大: {gradient_std:.2f}）"
    else:
        gradient_analysis_text = "玻璃表面平整（梯度正常）"
    return gradient_result, gradient_analysis_text, gradient_image_path

def frequency_analysis(gray, glass_id, output_dir='./output', threshold=400):
    """
    对图像做频域分析，检测表面平整度的高低频变化
    Args:
        gray: 灰度图像（numpy ndarray）
        glass_id: 当前玻璃的唯一标识（用于命名输出文件）
        output_dir: 结果保存目录（默认'./output'）
        threshold: 频谱最大最小差的分界阈值，默认400
    Returns:
        frequency_result: 频域分析结果，0代表不平整，1代表平整
        frequency_analysis_text: 分析结论的文字描述
        frequency_image_path: 频谱图片保存路径
    """
    dft = cv2.dft(np.float32(gray), flags=cv2.DFT_COMPLEX_OUTPUT)
    dft_shift = np.fft.fftshift(dft)
    magnitude_spectrum = 20 * np.log(cv2.magnitude(dft_shift[:, :, 0], dft_shift[:, :, 1]) + 1)
    frequency_image_path = os.path.join(output_dir, f"{glass_id}-frequency.jpg")
    plt.imsave(frequency_image_path, magnitude_spectrum, cmap='gray')
    freq_max = np.max(magnitude_spectrum)
    freq_min = np.min(magnitude_spectrum)
    freq_diff = freq_max - freq_min
    frequency_result = 1 if freq_diff < threshold else 0
    if frequency_result == 0:
        frequency_analysis_text = f"玻璃表面可能不平整（频谱最大-最小差值较大: {freq_diff:.2f}）"
    else:
        frequency_analysis_text = f"玻璃表面平整（频谱最大-最小差值较小: {freq_diff:.2f}）"
    return frequency_result, frequency_analysis_text, frequency_image_path
