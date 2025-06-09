import unittest
import sys
import os
import cv2
import numpy as np

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from detection.methods import edge_analysis, line_analysis, gradient_analysis, frequency_analysis


class TestDetectionMethods(unittest.TestCase):
    """检测方法单元测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建不同类型的测试图像
        self.blank_image = np.ones((300, 300, 3), dtype=np.uint8) * 255
        self.noisy_image = self.create_noisy_image()
        self.pattern_image = self.create_pattern_image()
        self.edge_image = self.create_edge_image()
        
    def create_noisy_image(self):
        """创建噪声图像"""
        img = np.ones((300, 300, 3), dtype=np.uint8) * 128
        noise = np.random.normal(0, 50, img.shape).astype(np.uint8)
        return cv2.add(img, noise)
        
    def create_pattern_image(self):
        """创建有规律图案的图像"""
        img = np.ones((300, 300, 3), dtype=np.uint8) * 255
        for i in range(0, 300, 30):
            cv2.line(img, (i, 0), (i, 300), (0, 0, 0), 1)
            cv2.line(img, (0, i), (300, i), (0, 0, 0), 1)
        return img
        
    def create_edge_image(self):
        """创建有明显边缘的图像"""
        img = np.ones((300, 300, 3), dtype=np.uint8) * 255
        cv2.rectangle(img, (50, 50), (250, 250), (0, 0, 0), 2)
        cv2.circle(img, (150, 150), 50, (0, 0, 0), 2)
        return img
        
    def test_edge_analysis_parameters(self):
        """测试边缘分析的参数"""
        result = edge_analysis(self.edge_image)
        
        # 检查返回值结构
        self.assertIn('is_flat', result)
        self.assertIn('edge_count', result)
        self.assertIn('sharpness', result)
        self.assertIn('edges', result)
        
        # 检查数值范围
        self.assertGreaterEqual(result['edge_count'], 0)
        self.assertGreaterEqual(result['sharpness'], 0)
        
    def test_line_analysis_angles(self):
        """测试直线角度分析"""
        # 创建只有水平和垂直线的图像
        img = np.ones((300, 300, 3), dtype=np.uint8) * 255
        cv2.line(img, (0, 150), (300, 150), (0, 0, 0), 2)
        cv2.line(img, (150, 0), (150, 300), (0, 0, 0), 2)
        
        result = line_analysis(img)
        
        self.assertIn('angle_std', result)
        self.assertIn('angles', result)
        self.assertEqual(len(result['angles']), result['line_count'])
        
    def test_gradient_analysis_smooth_vs_textured(self):
        """测试梯度分析对平滑和纹理图像的区分"""
        # 平滑图像
        smooth_result = gradient_analysis(self.blank_image)
        self.assertTrue(smooth_result['is_flat'])
        self.assertLess(smooth_result['gradient_std'], 50)
        
        # 纹理图像
        textured_result = gradient_analysis(self.noisy_image)
        self.assertFalse(textured_result['is_flat'])
        self.assertGreater(textured_result['gradient_std'], 50)
        
    def test_frequency_analysis_patterns(self):
        """测试频域分析对不同图案的响应"""
        # 空白图像应该有较小的频率范围
        blank_result = frequency_analysis(self.blank_image)
        self.assertLess(blank_result['frequency_range'], 200)
        
        # 有规律图案的图像应该有较大的频率范围
        pattern_result = frequency_analysis(self.pattern_image)
        self.assertGreater(pattern_result['frequency_range'], 100)
        
    def test_edge_analysis_threshold_sensitivity(self):
        """测试边缘分析的阈值敏感性"""
        # 使用不同对比度的图像
        for contrast in [10, 50, 100, 200]:
            img = np.ones((300, 300, 3), dtype=np.uint8) * 128
            cv2.rectangle(img, (50, 50), (250, 250), (128 + contrast, 128 + contrast, 128 + contrast), -1)
            
            result = edge_analysis(img)
            self.assertIsInstance(result['edge_count'], int)
            
    def test_line_analysis_minimum_lines(self):
        """测试最少直线数量的情况"""
        # 只有一条线
        img = np.ones((300, 300, 3), dtype=np.uint8) * 255
        cv2.line(img, (0, 150), (300, 150), (0, 0, 0), 2)
        
        result = line_analysis(img)
        self.assertEqual(result['line_count'], 1)
        self.assertEqual(result['angle_std'], 0)  # 只有一条线，标准差为0
        
    def test_methods_with_grayscale_conversion(self):
        """测试方法对灰度图像的处理"""
        gray_img = cv2.cvtColor(self.pattern_image, cv2.COLOR_BGR2GRAY)
        gray_3ch = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)
        
        # 所有方法都应该能处理转换后的灰度图
        edge_result = edge_analysis(gray_3ch)
        line_result = line_analysis(gray_3ch)
        gradient_result = gradient_analysis(gray_3ch)
        frequency_result = frequency_analysis(gray_3ch)
        
        self.assertIsInstance(edge_result, dict)
        self.assertIsInstance(line_result, dict)
        self.assertIsInstance(gradient_result, dict)
        self.assertIsInstance(frequency_result, dict)


if __name__ == '__main__':
    unittest.main()