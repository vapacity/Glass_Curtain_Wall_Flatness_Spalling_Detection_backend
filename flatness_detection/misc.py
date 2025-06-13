"""
 @Time    : 2020/3/15 20:09
 @Author  : TaylorMei
 @E-mail  : mhy666@mail.dlut.edu.cn
 
 @Project : CVPR2020_GDNet
 @File    : misc.py
 @Function:
 
"""
import os
import xlwt
import numpy as np
from skimage import io


################################################################
######################## Utils #################################
################################################################
def check_mkdir(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)


def data_write(file_path, datas):
    f = xlwt.Workbook()
    sheet1 = f.add_sheet(sheetname="sheet1", cell_overwrite_ok=True)

    j = 0
    for data in datas:
        for i in range(len(data)):
            sheet1.write(i, j, data[i])
        j = j + 1

    f.save(file_path)


################################################################
######################## Train & Test ##########################
################################################################
class AvgMeter(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


# codes of this function are borrowed from https://github.com/Andrew-Qibin/dss_crf
def crf_refine(img, annos, tau=1.05, num_iterations=5, sigma=3.0):
    assert img.dtype == np.uint8
    assert annos.dtype == np.uint8
    assert img.shape[:2] == annos.shape

    # Convert img and annos to PyTorch tensors
    img_tensor = torch.from_numpy(img).float() / 255.  # Normalize to [0, 1]
    annos_tensor = torch.from_numpy(annos).float() / 255.  # Normalize annotations

    # Constants
    EPSILON = 1e-8
    M = 2  # number of classes (salient or not)
    
    # Unary energies (calculated based on the annotations)
    n_energy = -torch.log(1.0 - annos_tensor + EPSILON) / (tau * _sigmoid(1 - annos_tensor))
    p_energy = -torch.log(annos_tensor + EPSILON) / (tau * _sigmoid(annos_tensor))

    # Reshape energies into the shape suitable for CRF
    U = torch.zeros((M, img.shape[0] * img.shape[1]), dtype=torch.float32)
    U[0, :] = n_energy.flatten()
    U[1, :] = p_energy.flatten()

    # Now set up the CRF model

    # Step 1: Pairwise Gaussian (smoothes the probabilities between adjacent pixels)
    def pairwise_gaussian(img, sigma=3.0):
        kernel_size = int(6 * sigma + 1)
        kernel = cv2.getGaussianKernel(kernel_size, sigma)
        kernel = kernel @ kernel.T
        kernel = torch.tensor(kernel, dtype=torch.float32)

        # Add padding to the image for convolution
        img_padded = F.pad(img.unsqueeze(0).unsqueeze(0), (kernel_size // 2,) * 4, mode='reflect')
        smoothed_img = F.conv2d(img_padded, kernel.unsqueeze(0).unsqueeze(0), groups=1)

        return smoothed_img.squeeze(0).squeeze(0)

    # Step 2: Pairwise Bilateral (uses color information and spatial distance)
    def pairwise_bilateral(img, sigma_color=5, sigma_spatial=60):
        # Bilateral filter uses both spatial and color information to refine labels
        spatial_filter = pairwise_gaussian(img, sigma=sigma_spatial)
        color_filter = pairwise_gaussian(img, sigma=sigma_color)
        return spatial_filter * color_filter

    # Step 3: Iterative refinement loop
    refined_probs = U  # Start with the unary energies

    for _ in range(num_iterations):
        # Apply pairwise Gaussian (smooth the probabilities based on pixel similarity)
        smooth_probs = pairwise_gaussian(refined_probs, sigma=sigma)

        # Apply pairwise bilateral (smooth based on both spatial and color similarity)
        bilateral_probs = pairwise_bilateral(refined_probs, sigma_spatial=sigma, sigma_color=sigma)

        # Combine unary, smooth, and bilateral terms
        refined_probs = 0.7 * refined_probs + 0.3 * smooth_probs + 0.2 * bilateral_probs

    # Step 4: Convert the probabilities into a segmentation map
    refined_map = refined_probs[1, :].reshape(img.shape[0], img.shape[1])  # Take the foreground class (index 1)
    
    # Ensure the result is in the same format as the original code (uint8)
    refined_map = (refined_map * 255).clamp(0, 255).byte()  # Scale and convert to uint8
    
    return refined_map.numpy()  # Return as a numpy array


def get_gt_mask(imgname, MASK_DIR):
    filestr = imgname[:-4]
    mask_folder = MASK_DIR
    mask_path = os.path.join(mask_folder, filestr + ".png")
    mask = io.imread(mask_path)
    mask = np.where(mask == 255, 1, 0).astype(np.float32)

    return mask


def get_normalized_predict_mask(imgname, PREDICT_MASK_DIR):
    filestr = imgname[:-4]
    mask_folder = PREDICT_MASK_DIR
    mask_path = os.path.join(mask_folder, filestr + ".png")
    if not os.path.exists(mask_path):
        print("{} has no predict mask!".format(imgname))
    mask = io.imread(mask_path).astype(np.float32)
    if np.max(mask) - np.min(mask) > 0:
        mask = (mask - np.min(mask)) / (np.max(mask) - np.min(mask))
    else:
        mask = mask / 255.0
    mask = mask.astype(np.float32)

    return mask


def get_binary_predict_mask(imgname, PREDICT_MASK_DIR):
    filestr = imgname[:-4]
    mask_folder = PREDICT_MASK_DIR
    mask_path = os.path.join(mask_folder, filestr + ".png")
    if not os.path.exists(mask_path):
        print("{} has no predict mask!".format(imgname))
    mask = io.imread(mask_path).astype(np.float32)
    mask = np.where(mask >= 127.5, 1, 0).astype(np.float32)

    return mask


################################################################
######################## Evaluation ############################
################################################################
def compute_iou(predict_mask, gt_mask):
    check_size(predict_mask, gt_mask)

    if np.sum(predict_mask) == 0 or np.sum(gt_mask) == 0:
        iou_ = 0
        return iou_

    n_ii = np.sum(np.logical_and(predict_mask, gt_mask))
    t_i = np.sum(gt_mask)
    n_ij = np.sum(predict_mask)

    iou_ = n_ii / (t_i + n_ij - n_ii)

    return iou_


def compute_acc(predict_mask, gt_mask):
    # recall
    check_size(predict_mask, gt_mask)

    N_p = np.sum(gt_mask)
    N_n = np.sum(np.logical_not(gt_mask))

    TP = np.sum(np.logical_and(predict_mask, gt_mask))
    TN = np.sum(np.logical_and(np.logical_not(predict_mask), np.logical_not(gt_mask)))

    accuracy_ = TP / N_p

    return accuracy_


def compute_acc_image(predict_mask, gt_mask):
    check_size(predict_mask, gt_mask)

    N_p = np.sum(gt_mask)
    N_n = np.sum(np.logical_not(gt_mask))

    TP = np.sum(np.logical_and(predict_mask, gt_mask))
    TN = np.sum(np.logical_and(np.logical_not(predict_mask), np.logical_not(gt_mask)))

    accuracy_ = (TP + TN) / (N_p + N_n)

    return accuracy_


def compute_precision_recall(prediction, gt):
    assert prediction.dtype == np.float32
    assert gt.dtype == np.float32
    assert prediction.shape == gt.shape

    eps = 1e-4

    hard_gt = np.zeros(prediction.shape)
    hard_gt[gt > 0.5] = 1
    t = np.sum(hard_gt)

    precision, recall = [], []
    # calculating precision and recall at 255 different binarizing thresholds
    for threshold in range(256):
        threshold = threshold / 255.

        hard_prediction = np.zeros(prediction.shape)
        hard_prediction[prediction > threshold] = 1

        tp = np.sum(hard_prediction * hard_gt)
        p = np.sum(hard_prediction)

        precision.append((tp + eps) / (p + eps))
        recall.append((tp + eps) / (t + eps))

    return precision, recall


def compute_fmeasure(precision, recall):
    assert len(precision) == 256
    assert len(recall) == 256
    beta_square = 0.3
    max_fmeasure = max([(1 + beta_square) * p * r / (beta_square * p + r) for p, r in zip(precision, recall)])

    return max_fmeasure


def compute_mae(predict_mask, gt_mask):
    check_size(predict_mask, gt_mask)

    mae_ = np.mean(abs(predict_mask - gt_mask)).item()

    return mae_


def compute_ber(predict_mask, gt_mask):
    check_size(predict_mask, gt_mask)

    N_p = np.sum(gt_mask)
    N_n = np.sum(np.logical_not(gt_mask))

    TP = np.sum(np.logical_and(predict_mask, gt_mask))
    TN = np.sum(np.logical_and(np.logical_not(predict_mask), np.logical_not(gt_mask)))

    ber_ = 100 * (1 - (1 / 2) * ((TP / N_p) + (TN / N_n)))

    return ber_


def segm_size(segm):
    try:
        height = segm.shape[0]
        width = segm.shape[1]
    except IndexError:
        raise

    return height, width


def check_size(eval_segm, gt_segm):
    h_e, w_e = segm_size(eval_segm)
    h_g, w_g = segm_size(gt_segm)

    if (h_e != h_g) or (w_e != w_g):
        raise EvalSegErr("DiffDim: Different dimensions of matrices!")


class EvalSegErr(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
