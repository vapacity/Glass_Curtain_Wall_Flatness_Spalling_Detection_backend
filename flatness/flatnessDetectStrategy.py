import os
import cv2
import numpy as np
import matplotlib.pyplot as plt

def crop_glass_region(image,border_ratio=0.1):
    """
    裁剪图像的中间区域，排除边框部分。
    参数：
        image: 输入图像
        border_ratio: 边框占比，例如 0.1 表示裁剪掉上下左右各 10%
    返回：
        裁剪后的中间区域图像
    """
    h, w, _ = image.shape
    top = int(h * border_ratio)  # 裁剪顶部
    bottom = int(h * (1 - border_ratio))  # 裁剪底部
    left = int(w * border_ratio)  # 裁剪左侧
    right = int(w * (1 - border_ratio))  # 裁剪右侧

    cropped_image = image[top:bottom, left:right]
    return cropped_image


def detect_glass_flatness(image, glass_id, output_dir='./output'):
    """
    检测玻璃的平整性，并返回分析结果及中间图像路径。
    """
    # 创建一个唯一ID表示这块玻璃的分析
    #glass_id = str(uuid.uuid4())

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    image = cv2.imread(image)
    # Step 1: 裁剪玻璃区域
    cropped_image = crop_glass_region(image, border_ratio=0.1)

    # Step 2: 边缘检测
    print("shift")
    print(cropped_image.shape)
    gray = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    # 保存边缘检测结果
    edge_image_path = output_dir + '/' + f"{glass_id}-edges.jpg"
    cv2.imwrite(edge_image_path, edges)

    # 边缘数量（非零像素数）
    edge_count = np.sum(edges > 0)

    # 使用拉普拉斯变换计算清晰度
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    laplacian_variance = laplacian.var()

    # 根据边缘数量和清晰度判断玻璃平整性
    if laplacian_variance < 10:  # 清晰度较低
        edge_result = 0
        edge_analysis = f"玻璃表面可能不平整（边缘模糊，拉普拉斯方差：{laplacian_variance:.2f}）"
    elif edge_count < 500:  # 边缘数量较少
        edge_result = 1
        edge_analysis = f"玻璃表面平整（边缘正常，但简单背景，边缘数量：{edge_count}）"
    else:
        edge_result = 1
        edge_analysis = f"玻璃表面平整（边缘清晰且正常，拉普拉斯方差：{laplacian_variance:.2f}，边缘数量：{edge_count}）"

    # Step 3: 直线检测
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=10)
    line_image = cropped_image.copy()
    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(line_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            angles.append(angle)
    line_image_path = output_dir + '/' + f"{glass_id}-lines.jpg"
    cv2.imwrite(line_image_path, line_image)
    num_lines = len(lines) if lines is not None else 0
    angle_std = np.std(angles) if angles else 0.0
    line_result = 1 if angle_std < 50 else 0
    line_analysis = f"玻璃表面可能不平整（角度标准差较大: {angle_std:.2f}）" if line_result == 0 else "玻璃表面平整（直线角度正常）"

    # Step 4: 梯度分析
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    grad_magnitude = cv2.magnitude(grad_x, grad_y)
    gradient_image_path = output_dir + '/' + f"{glass_id}-gradient.jpg"
    cv2.imwrite(gradient_image_path, np.uint8(grad_magnitude))
    gradient_mean = np.mean(grad_magnitude)
    gradient_std = np.std(grad_magnitude)
    gradient_result = 1 if gradient_std < 100 else 0
    gradient_analysis = f"玻璃表面可能不平整（梯度标准差较大: {gradient_std:.2f}）" if gradient_result == 0 else "玻璃表面平整（梯度正常）"

    # Step 5: 频域分析
    dft = cv2.dft(np.float32(gray), flags=cv2.DFT_COMPLEX_OUTPUT)
    dft_shift = np.fft.fftshift(dft)
    magnitude_spectrum = 20 * np.log(cv2.magnitude(dft_shift[:, :, 0], dft_shift[:, :, 1]))

    # 保存频谱图
    frequency_image_path = output_dir + '/' + f"{glass_id}-frequency.jpg"
    plt.imsave(frequency_image_path, magnitude_spectrum, cmap='gray')

    # 计算最大值和最小值的差
    freq_max = np.max(magnitude_spectrum)
    freq_min = np.min(magnitude_spectrum)
    freq_diff = freq_max - freq_min

    # 使用差值作为平整性判断指标
    threshold = 400
    frequency_result = 1 if freq_diff < threshold else 0
    frequency_analysis = (
        f"玻璃表面可能不平整（频谱最大-最小差值较大: {freq_diff:.2f}）"
        if frequency_result == 0
        else f"玻璃表面平整（频谱最大-最小差值较小: {freq_diff:.2f}）"
    )

    # 综合结果：服从多数
    flatness_result = 1 if sum([line_result, gradient_result, frequency_result]) >= 2 else 0

    return {
        'edge_image_path': edge_image_path,
        'line_image_path': line_image_path,
        'gradient_image_path': gradient_image_path,
        'frequency_image_path': frequency_image_path,
        'edge_analysis': edge_analysis,
        'line_analysis': line_analysis,
        'gradient_analysis': gradient_analysis,
        'frequency_analysis': frequency_analysis,
        'edge_result': edge_result,
        'line_result': line_result,
        'gradient_result': gradient_result,
        'frequency_result': frequency_result,
        'flatness_result': flatness_result
    }
