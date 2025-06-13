import cv2
import numpy as np
from PIL import Image
import os

def extract_white_regions(black_white_image):
    """
    从黑白图中提取白色区域的轮廓。
    """
    # 确保图像是灰度图，如果是彩色图像则转换为灰度图
    if len(black_white_image.shape) == 3:
        gray = cv2.cvtColor(black_white_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = black_white_image

    # 使用阈值将图像二值化：白色部分为255，其他部分为0
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # 查找白色区域的轮廓
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    return contours

def expand_bounding_box(x, y, w, h, image_shape, padding_ratio=0.1):
    """
    扩展边界框，使其覆盖更多的区域。padding_ratio控制扩展比例。
    确保扩展后的矩形框不超出图像边界。
    """
    img_h, img_w = image_shape
    padding_w = int(w * padding_ratio)  # 宽度扩展量
    padding_h = int(h * padding_ratio)  # 高度扩展量
    
    # 扩展后的矩形坐标
    new_x = max(x - padding_w, 0)
    new_y = max(y - padding_h, 0)
    new_w = min(w + 2 * padding_w, img_w - new_x)
    new_h = min(h + 2 * padding_h, img_h - new_y)

    return new_x, new_y, new_w, new_h

def segment_from_original_image(original_image, contours, min_area=200):
    """
    根据黑白图的轮廓信息，从原图中提取相应区域。
    """
    segments = []
    img_h, img_w = original_image.shape[:2]
    for idx, contour in enumerate(contours):
        # 获取轮廓的边界框
        x, y, w, h = cv2.boundingRect(contour)

        # 扩展边界框，确保白色区域能被完整截取
        x, y, w, h = expand_bounding_box(x, y, w, h, (img_h, img_w), padding_ratio=0.1)
        if w * h < min_area:
            continue
        # 从原图中裁剪出白色区域
        segment = original_image[y:y+h, x:x+w]

        # 将每个分割的区域保存为 PIL 图像对象
        pil_segment = Image.fromarray(segment)
        segments.append((pil_segment, (x, y, w, h)))  # 返回图像对象和坐标元组
    return segments

def save_segments(segments, output_dir):
    """
    保存分割后的区域到指定目录。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for idx, (segment, (x, y, w, h)) in enumerate(segments):
        segment.save(os.path.join(output_dir, f"{idx}.png"))

# def main():
#     # 加载黑白图和原图
#     black_white_image = np.array(Image.open("/root/CVPR2020_GDNet/results/Test/GDNet_200/10002..png"))
#     original_image = np.array(Image.open("/root/CVPR2020_GDNet/Test/test/image/10002.jpeg"))
#
#     # 提取黑白图中的白色区域轮廓
#     contours = extract_white_regions(black_white_image)
#
#     # 根据轮廓从原图中分割出相应区域
#     segments = segment_from_original_image(original_image, contours)
#
#     # 保存分割后的区域
#     save_segments(segments, "output_segments/"+"10002", "original_image")
#
# if __name__ == "__main__":
#     main()
