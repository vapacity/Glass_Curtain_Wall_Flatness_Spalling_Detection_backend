import cv2
import numpy as np
from PIL import Image, ImageDraw


def draw_flatness_results(original_image_path, segments, flatness_results):
    # 读取原图
    original_image = cv2.imread(original_image_path)

    # 将原图转换为RGB格式，以便与PIL一起使用
    original_image_rgb = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)

    # 将图像转换为RGBA模式（带透明度通道）
    pil_img = Image.fromarray(original_image_rgb).convert("RGBA")

    # 创建一个透明图层（RGBA模式，初始全透明）
    overlay = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))  # 完全透明背景
    draw = ImageDraw.Draw(overlay)

    # 使用半透明的矩形来标注平整区域
    for i, (pil_segment, (x, y, w, h)) in enumerate(segments):
        flatness = flatness_results[i]
        # 设置颜色（绿色为平整，红色为不平整）
        if flatness:
            color = (0, 255, 0, 128)  # 半透明绿色 (R, G, B, A)
        else:
            color = (255, 0, 0, 128)  # 半透明红色 (R, G, B, A)

        # 绘制半透明矩形框
        draw.rectangle([x, y, x + w, y + h], fill=color, outline=(0, 0, 0))

    # 将透明图层与原图合成（叠加）
    final_image = Image.alpha_composite(pil_img, overlay)

    # 将结果图像转换回BGR模式（适合cv2保存）
    final_image_bgr = cv2.cvtColor(np.array(final_image), cv2.COLOR_RGBA2BGR)

    # 保存结果图像
    result_image_path = original_image_path.replace(".jpg", "_with_flatness.png")  # 使用PNG格式保存，以支持透明度
    cv2.imwrite(result_image_path, final_image_bgr)

    return result_image_path
