import unittest
import sys
import os
import cv2
import numpy as np
from unittest.mock import patch, MagicMock

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from detection.flatnessDetectStrategy import detect_glass_flatness, crop_glass_region
from detection.methods import edge_analysis, line_analysis, gradient_analysis, frequency_analysis


class TestFlatnessDetection(unittest.TestCase):
    """平整度检测功能单元测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试图像
        self.test_image_flat = np.ones((500, 500, 3), dtype=np.uint8) * 255  # 白色平整图像
        self.test_image_uneven = self.create_uneven_image()  # 不平整图像
        
    def create_uneven_image(self):
        """创建模拟不平整的图像"""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255
        # 添加随机噪声和线条
        for i in range(20):
            x1, y1 = np.random.randint(0, 500, 2)
            x2, y2 = np.random.randint(0, 500, 2)
            cv2.line(img, (x1, y1), (x2, y2), (0, 0, 0), 2)
        # 添加噪声
        noise = np.random.normal(0, 50, img.shape).astype(np.uint8)
        img = cv2.add(img, noise)
        return img
    
    def test_crop_glass_region(self):
        """测试图像裁剪功能"""
        cropped = crop_glass_region(self.test_image_flat)
        self.assertEqual(cropped.shape[0], 400)  # 500 * 0.8
        self.assertEqual(cropped.shape[1], 400)  # 500 * 0.8
        
    def test_edge_analysis_flat(self):
        """测试平整图像的边缘分析"""
        result = edge_analysis(self.test_image_flat)
        self.assertIsInstance(result, dict)
        self.assertIn('is_flat', result)
        self.assertIn('edge_count', result)
        self.assertIn('sharpness', result)
        self.assertTrue(result['is_flat'])  # 平整图像应该通过测试
        
    def test_edge_analysis_uneven(self):
        """测试不平整图像的边缘分析"""
        result = edge_analysis(self.test_image_uneven)
        self.assertIsInstance(result, dict)
        self.assertFalse(result['is_flat'])  # 不平整图像应该不通过测试
        
    def test_line_analysis(self):
        """测试直线分析功能"""
        # 创建有直线的测试图像
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255
        cv2.line(img, (0, 250), (500, 250), (0, 0, 0), 2)  # 水平线
        cv2.line(img, (250, 0), (250, 500), (0, 0, 0), 2)  # 垂直线
        
        result = line_analysis(img)
        self.assertIsInstance(result, dict)
        self.assertIn('is_flat', result)
        self.assertIn('line_count', result)
        self.assertIn('angle_std', result)
        
    def test_gradient_analysis(self):
        """测试梯度分析功能"""
        result = gradient_analysis(self.test_image_flat)
        self.assertIsInstance(result, dict)
        self.assertIn('is_flat', result)
        self.assertIn('gradient_std', result)
        self.assertTrue(result['is_flat'])  # 平整图像梯度应该较小
        
    def test_frequency_analysis(self):
        """测试频域分析功能"""
        result = frequency_analysis(self.test_image_flat)
        self.assertIsInstance(result, dict)
        self.assertIn('is_flat', result)
        self.assertIn('frequency_range', result)
        
    @patch('cv2.imwrite')
    def test_detect_glass_flatness_integration(self, mock_imwrite):
        """测试完整的平整度检测流程"""
        mock_imwrite.return_value = True
        
        result = detect_glass_flatness(self.test_image_flat, save_intermediate=True)
        
        self.assertIsInstance(result, dict)
        self.assertIn('is_flat', result)
        self.assertIn('confidence', result)
        self.assertIn('analysis_results', result)
        self.assertIn('edge_analysis', result['analysis_results'])
        self.assertIn('line_analysis', result['analysis_results'])
        self.assertIn('gradient_analysis', result['analysis_results'])
        self.assertIn('frequency_analysis', result['analysis_results'])
        
        # 验证中间结果保存被调用
        self.assertEqual(mock_imwrite.call_count, 6)  # 6个中间结果图像
        
    def test_confidence_calculation(self):
        """测试置信度计算"""
        result = detect_glass_flatness(self.test_image_flat, save_intermediate=False)
        confidence = result['confidence']
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        
    def test_different_image_sizes(self):
        """测试不同尺寸的图像"""
        sizes = [(300, 300), (800, 600), (1920, 1080)]
        for size in sizes:
            img = np.ones((size[1], size[0], 3), dtype=np.uint8) * 255
            result = detect_glass_flatness(img, save_intermediate=False)
            self.assertIsInstance(result, dict)
            self.assertIn('is_flat', result)


class TestEdgeCases(unittest.TestCase):
    """边界情况测试"""
    
    def test_empty_image(self):
        """测试空图像"""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = detect_glass_flatness(img, save_intermediate=False)
        self.assertIsInstance(result, dict)
        
    def test_single_channel_image(self):
        """测试单通道图像"""
        img = np.ones((500, 500), dtype=np.uint8) * 255
        # 转换为3通道
        img_3ch = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        result = detect_glass_flatness(img_3ch, save_intermediate=False)
        self.assertIsInstance(result, dict)
        
    def test_very_small_image(self):
        """测试极小图像"""
        img = np.ones((50, 50, 3), dtype=np.uint8) * 255
        result = detect_glass_flatness(img, save_intermediate=False)
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    unittest.main()