import os
import time

import numpy as np
import cv2
import torch
from PIL import Image,ImageDraw
from torch.autograd import Variable
from torchvision import transforms

from config import gdd_testing_root, gdd_results_root
from misc import check_mkdir, crf_refine
from gdnet import GDNet

# from
device_ids = [0]
torch.cuda.set_device(device_ids[0])

ckpt_path = './ckpt'
exp_name = 'GDNet'
args = {
    'snapshot': '200',
    'scale': 416,
    # 'crf': True,
    'crf': False,
}

print(torch.__version__)

img_transform = transforms.Compose([
    transforms.Resize((args['scale'], args['scale'])),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

to_test = {'GDD': gdd_testing_root}

to_pil = transforms.ToPILImage()

def extract_boundary(segmented_image):
    """
    提取分割图像的边界点。
    使用阈值分割，找到图像中的边界（例如，可以使用Canny边缘检测或简单的阈值）。
    """
    # 将图像转为二值图像
    binary_image = np.where(segmented_image > 0.5, 255, 0).astype(np.uint8)  # 假设分割值大于0.5是目标区域

    # 使用Canny边缘检测
    edges = cv2.Canny(binary_image, 100, 200)

    # 获取边界点的坐标
    boundary_points = np.column_stack(np.where(edges > 0))  # 获取所有边缘点的坐标

    return boundary_points, binary_image

def draw_boundary_on_image(image, boundary_points):
    """
    在图像上绘制边界点。
    """
    image_with_boundary = image.copy()  # 创建图像副本，避免修改原图
    draw = ImageDraw.Draw(image_with_boundary)

    # 在图像上绘制边界点
    for point in boundary_points:
        draw.point((point[1], point[0]), fill='red')  # 绘制红色边界点

    return image_with_boundary
def save_boundary_points(boundary_points, img_name, output_dir):
    """
    保存边界点坐标为.npy文件。
    """
    # 保存为NumPy文件
    np.save(os.path.join(output_dir, img_name + "_boundary.npy"), boundary_points)

def save_image_with_boundary(image, file_path):
    """
    保存带有边界的图像。
    """
    image.save(file_path)

def main():
    net = GDNet().cuda(device_ids[0])

    if len(args['snapshot']) > 0:
        print('Load snapshot {} for testing'.format(args['snapshot']))
        net.load_state_dict(torch.load(os.path.join(ckpt_path, exp_name, args['snapshot'] + '.pth')))
        print('Load {} succeed!'.format(os.path.join(ckpt_path, exp_name, args['snapshot'] + '.pth')))

    net.eval()
    with torch.no_grad():
        for name, root in to_test.items():
            img_list = [img_name for img_name in os.listdir(os.path.join(root, 'image'))]
            start = time.time()
            for idx, img_name in enumerate(img_list):
                print('predicting for {}: {:>4d} / {}'.format(name, idx + 1, len(img_list)))
                check_mkdir(os.path.join(gdd_results_root, '%s_%s' % (exp_name, args['snapshot'])))
                img = Image.open(os.path.join(root, 'image', img_name))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    print("{} is a gray image.".format(name))
                w, h = img.size
                img_var = Variable(img_transform(img).unsqueeze(0)).cuda(device_ids[0])
                f1, f2, f3 = net(img_var)
                f1 = f1.data.squeeze(0).cpu()
                f2 = f2.data.squeeze(0).cpu()
                f3 = f3.data.squeeze(0).cpu()
                f1 = np.array(transforms.Resize((h, w))(to_pil(f1)))
                f2 = np.array(transforms.Resize((h, w))(to_pil(f2)))
                f3 = np.array(transforms.Resize((h, w))(to_pil(f3)))
                if args['crf']:
                    # f1 = crf_refine(np.array(img.convert('RGB')), f1)
                    # f2 = crf_refine(np.array(img.convert('RGB')), f2)
                    f3 = crf_refine(np.array(img.convert('RGB')), f3)

                # sImage.fromarray(f1).save(os.path.join(ckpt_path, exp_name, '%s_%s' % (exp_name, args['snapshot']),
                #                                       img_name[:-4] + "_h.png"))
                # Image.fromarray(f2).save(os.path.join(ckpt_path, exp_name, '%s_%s' % (exp_name, args['snapshot']),
                #                                       img_name[:-4] + "_l.png"))

                Image.fromarray(f3).save(os.path.join(gdd_results_root, '%s_%s' % (exp_name, args['snapshot']),
                                                      img_name[:-4] + ".png"))
                                                      
                # 提取边界点
                boundary_points, _ = extract_boundary(f3)

                # 保存边界点到本地
                save_boundary_points(boundary_points, img_name[:-4], os.path.join(gdd_results_root, '%s_%s' % (exp_name, args['snapshot'])))

                # 在图像上绘制边界
                img_with_boundary = draw_boundary_on_image(img, boundary_points)

                # 保存带边界的图像
                save_image_with_boundary(img_with_boundary, os.path.join(gdd_results_root, '%s_%s' % (exp_name, args['snapshot']), img_name[:-4] + "_with_boundary.png"))
                # contours = extract_contours(f3)
                # regions = segment_image_by_contours(f3,contours)
                # save_segments(regions,gdd_results_root,img_name[:-4])
            end = time.time()
            print("Average Time Is : {:.2f}".format((end - start) / len(img_list)))


if __name__ == '__main__':
    main()