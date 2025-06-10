import time
import sys
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import psutil
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from detection.flatnessDetectStrategy import detect_glass_flatness
from detection.methods import edge_analysis, line_analysis, gradient_analysis, frequency_analysis


class PerformanceTestSuite:
    """性能测试套件"""
    
    def __init__(self):
        self.results = {
            'single_image_tests': [],
            'batch_tests': [],
            'memory_tests': [],
            'concurrent_tests': [],
            'scalability_tests': []
        }
        
    def generate_test_images(self, sizes):
        """生成不同尺寸的测试图像"""
        images = {}
        for size in sizes:
            # 生成不同复杂度的图像
            images[f'{size[0]}x{size[1]}_simple'] = np.ones((size[1], size[0], 3), dtype=np.uint8) * 255
            
            # 复杂图像
            complex_img = np.ones((size[1], size[0], 3), dtype=np.uint8) * 255
            for i in range(50):
                x1, y1 = np.random.randint(0, size[0]), np.random.randint(0, size[1])
                x2, y2 = np.random.randint(0, size[0]), np.random.randint(0, size[1])
                cv2.line(complex_img, (x1, y1), (x2, y2), (0, 0, 0), 2)
            images[f'{size[0]}x{size[1]}_complex'] = complex_img
            
        return images
        
    def test_single_image_performance(self):
        """测试单张图像处理性能"""
        print("开始单张图像性能测试...")
        
        sizes = [(640, 480), (1280, 720), (1920, 1080), (2560, 1440), (3840, 2160)]
        test_images = self.generate_test_images(sizes)
        
        for name, image in test_images.items():
            # 测试完整流程
            start_time = time.time()
            result = detect_glass_flatness(image, save_intermediate=False)
            total_time = time.time() - start_time
            
            # 测试各个组件
            component_times = {}
            
            # 边缘分析
            start = time.time()
            edge_analysis(image)
            component_times['edge_analysis'] = time.time() - start
            
            # 直线分析
            start = time.time()
            line_analysis(image)
            component_times['line_analysis'] = time.time() - start
            
            # 梯度分析
            start = time.time()
            gradient_analysis(image)
            component_times['gradient_analysis'] = time.time() - start
            
            # 频域分析
            start = time.time()
            frequency_analysis(image)
            component_times['frequency_analysis'] = time.time() - start
            
            self.results['single_image_tests'].append({
                'image_name': name,
                'image_shape': image.shape,
                'total_time': total_time,
                'component_times': component_times,
                'fps': 1/total_time if total_time > 0 else 0
            })
            
    def test_batch_processing(self):
        """测试批量处理性能"""
        print("开始批量处理性能测试...")
        
        # 生成100张测试图像
        batch_sizes = [10, 50, 100]
        image_size = (1280, 720)
        
        for batch_size in batch_sizes:
            images = []
            for i in range(batch_size):
                img = np.ones((image_size[1], image_size[0], 3), dtype=np.uint8) * 255
                if i % 2 == 0:  # 一半复杂图像
                    for j in range(20):
                        x1, y1 = np.random.randint(0, image_size[0]), np.random.randint(0, image_size[1])
                        x2, y2 = np.random.randint(0, image_size[0]), np.random.randint(0, image_size[1])
                        cv2.line(img, (x1, y1), (x2, y2), (0, 0, 0), 2)
                images.append(img)
            
            # 串行处理
            start_time = time.time()
            for img in images:
                detect_glass_flatness(img, save_intermediate=False)
            serial_time = time.time() - start_time
            
            self.results['batch_tests'].append({
                'batch_size': batch_size,
                'serial_time': serial_time,
                'avg_time_per_image': serial_time / batch_size,
                'throughput': batch_size / serial_time
            })
            
    def test_memory_usage(self):
        """测试内存使用情况"""
        print("开始内存使用测试...")
        
        process = psutil.Process(os.getpid())
        sizes = [(640, 480), (1920, 1080), (3840, 2160)]
        
        for size in sizes:
            img = np.ones((size[1], size[0], 3), dtype=np.uint8) * 255
            
            # 测试前内存
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # 执行检测
            result = detect_glass_flatness(img, save_intermediate=True)
            
            # 测试后内存
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            
            self.results['memory_tests'].append({
                'image_size': f'{size[0]}x{size[1]}',
                'memory_before_mb': memory_before,
                'memory_after_mb': memory_after,
                'memory_increase_mb': memory_after - memory_before,
                'pixels': size[0] * size[1]
            })
            
    def test_concurrent_processing(self):
        """测试并发处理性能"""
        print("开始并发处理性能测试...")
        
        num_images = 20
        image_size = (1280, 720)
        images = []
        
        for i in range(num_images):
            img = np.ones((image_size[1], image_size[0], 3), dtype=np.uint8) * 255
            images.append(img)
        
        # 不同线程数测试
        thread_counts = [1, 2, 4, 8]
        
        for num_threads in thread_counts:
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = []
                for img in images:
                    future = executor.submit(detect_glass_flatness, img, False)
                    futures.append(future)
                
                # 等待所有任务完成
                for future in futures:
                    future.result()
                    
            concurrent_time = time.time() - start_time
            
            self.results['concurrent_tests'].append({
                'num_threads': num_threads,
                'num_images': num_images,
                'total_time': concurrent_time,
                'avg_time_per_image': concurrent_time / num_images,
                'speedup': self.results['batch_tests'][0]['serial_time'] / concurrent_time if self.results['batch_tests'] else 1
            })
            
    def test_scalability(self):
        """测试算法可扩展性"""
        print("开始可扩展性测试...")
        
        base_size = 256
        scales = [1, 2, 4, 8]  # 对应 256x256, 512x512, 1024x1024, 2048x2048
        
        for scale in scales:
            size = base_size * scale
            img = np.ones((size, size, 3), dtype=np.uint8) * 255
            
            # 添加相同密度的特征
            num_lines = 10 * scale
            for i in range(num_lines):
                x1, y1 = np.random.randint(0, size, 2)
                x2, y2 = np.random.randint(0, size, 2)
                cv2.line(img, (x1, y1), (x2, y2), (0, 0, 0), 1)
            
            start_time = time.time()
            result = detect_glass_flatness(img, save_intermediate=False)
            process_time = time.time() - start_time
            
            self.results['scalability_tests'].append({
                'scale': scale,
                'image_size': f'{size}x{size}',
                'pixels': size * size,
                'process_time': process_time,
                'time_per_megapixel': process_time / (size * size / 1000000)
            })
            
    def generate_report(self):
        """生成性能测试报告"""
        report = {
            'test_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 'N/A',
                'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024
            },
            'results': self.results
        }
        
        # 保存JSON报告
        with open('test/test_reports/performance_report.json', 'w') as f:
            json.dump(report, f, indent=2)
            
        # 生成可视化报告
        self.generate_visualizations()
        
        return report
        
    def generate_visualizations(self):
        """生成性能可视化图表"""
        # 单张图像处理时间对比
        plt.figure(figsize=(12, 8))
        
        # 子图1: 不同尺寸图像的处理时间
        plt.subplot(2, 2, 1)
        sizes = []
        times = []
        for test in self.results['single_image_tests']:
            if 'simple' in test['image_name']:
                sizes.append(test['image_name'].split('_')[0])
                times.append(test['total_time'])
        
        plt.bar(sizes, times)
        plt.xlabel('图像尺寸')
        plt.ylabel('处理时间 (秒)')
        plt.title('不同尺寸图像的处理时间')
        plt.xticks(rotation=45)
        
        # 子图2: 组件耗时分析
        plt.subplot(2, 2, 2)
        if self.results['single_image_tests']:
            test = self.results['single_image_tests'][0]  # 使用第一个测试结果
            components = list(test['component_times'].keys())
            times = list(test['component_times'].values())
            
            plt.pie(times, labels=components, autopct='%1.1f%%')
            plt.title('各组件耗时占比')
        
        # 子图3: 并发性能
        plt.subplot(2, 2, 3)
        if self.results['concurrent_tests']:
            threads = [t['num_threads'] for t in self.results['concurrent_tests']]
            speedups = [t['speedup'] for t in self.results['concurrent_tests']]
            
            plt.plot(threads, speedups, 'o-')
            plt.xlabel('线程数')
            plt.ylabel('加速比')
            plt.title('并发处理加速比')
            plt.grid(True)
        
        # 子图4: 可扩展性分析
        plt.subplot(2, 2, 4)
        if self.results['scalability_tests']:
            pixels = [t['pixels']/1000000 for t in self.results['scalability_tests']]  # 转换为百万像素
            times = [t['process_time'] for t in self.results['scalability_tests']]
            
            plt.plot(pixels, times, 'o-')
            plt.xlabel('图像大小 (百万像素)')
            plt.ylabel('处理时间 (秒)')
            plt.title('算法可扩展性')
            plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('test/test_reports/performance_visualization.png', dpi=150)
        plt.close()
        
    def run_all_tests(self):
        """运行所有性能测试"""
        print("开始运行性能测试套件...")
        
        self.test_single_image_performance()
        self.test_batch_processing()
        self.test_memory_usage()
        self.test_concurrent_processing()
        self.test_scalability()
        
        report = self.generate_report()
        
        print("\n性能测试完成！")
        print(f"报告已保存至: test/test_reports/performance_report.json")
        print(f"可视化图表已保存至: test/test_reports/performance_visualization.png")
        
        return report


if __name__ == '__main__':
    suite = PerformanceTestSuite()
    suite.run_all_tests()