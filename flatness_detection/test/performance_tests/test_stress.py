import sys
import os
import time
import threading
import multiprocessing
import cv2
import numpy as np
import psutil
import matplotlib.pyplot as plt
from datetime import datetime
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from detection.flatnessDetectStrategy import detect_glass_flatness


class StressTest:
    """压力测试类"""
    
    def __init__(self):
        self.results = {
            'load_tests': [],
            'endurance_tests': [],
            'spike_tests': [],
            'resource_limit_tests': []
        }
        
    def monitor_resources(self, duration=60, interval=1):
        """监控系统资源使用情况"""
        cpu_usage = []
        memory_usage = []
        timestamps = []
        
        start_time = time.time()
        while time.time() - start_time < duration:
            cpu_usage.append(psutil.cpu_percent(interval=0.1))
            memory_usage.append(psutil.virtual_memory().percent)
            timestamps.append(time.time() - start_time)
            time.sleep(interval)
            
        return {
            'timestamps': timestamps,
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'avg_cpu': np.mean(cpu_usage),
            'max_cpu': np.max(cpu_usage),
            'avg_memory': np.mean(memory_usage),
            'max_memory': np.max(memory_usage)
        }
        
    def test_load_capacity(self):
        """测试系统负载能力"""
        print("开始负载能力测试...")
        
        image_size = (1280, 720)
        concurrent_levels = [1, 5, 10, 20, 50]
        
        for level in concurrent_levels:
            print(f"测试并发数: {level}")
            
            # 创建测试图像
            images = []
            for i in range(level):
                img = np.ones((image_size[1], image_size[0], 3), dtype=np.uint8) * 255
                # 添加随机特征
                for j in range(10):
                    x1, y1 = np.random.randint(0, image_size[0]), np.random.randint(0, image_size[1])
                    x2, y2 = np.random.randint(0, image_size[0]), np.random.randint(0, image_size[1])
                    cv2.line(img, (x1, y1), (x2, y2), (0, 0, 0), 2)
                images.append(img)
            
            # 记录开始时的资源使用
            process = psutil.Process()
            cpu_before = process.cpu_percent()
            memory_before = process.memory_info().rss / 1024 / 1024
            
            # 并发处理
            start_time = time.time()
            threads = []
            results = [None] * level
            
            def process_image(idx, img):
                results[idx] = detect_glass_flatness(img, save_intermediate=False)
            
            for i in range(level):
                thread = threading.Thread(target=process_image, args=(i, images[i]))
                thread.start()
                threads.append(thread)
            
            # 等待所有线程完成
            for thread in threads:
                thread.join()
            
            process_time = time.time() - start_time
            
            # 记录结束时的资源使用
            cpu_after = process.cpu_percent()
            memory_after = process.memory_info().rss / 1024 / 1024
            
            # 计算成功率
            success_count = sum(1 for r in results if r is not None and 'is_flat' in r)
            success_rate = success_count / level * 100
            
            self.results['load_tests'].append({
                'concurrent_level': level,
                'process_time': process_time,
                'avg_time_per_request': process_time / level,
                'success_rate': success_rate,
                'cpu_usage': cpu_after - cpu_before,
                'memory_increase_mb': memory_after - memory_before,
                'throughput': level / process_time
            })
            
    def test_endurance(self, duration_minutes=5):
        """持久性测试"""
        print(f"开始持久性测试 (持续{duration_minutes}分钟)...")
        
        image_size = (1280, 720)
        start_time = time.time()
        end_time = start_time + duration_minutes * 60
        
        processed_count = 0
        error_count = 0
        response_times = []
        
        # 启动资源监控线程
        monitor_thread = threading.Thread(
            target=lambda: self.monitor_resources(duration_minutes * 60, 1)
        )
        monitor_thread.start()
        
        while time.time() < end_time:
            # 生成随机图像
            img = np.ones((image_size[1], image_size[0], 3), dtype=np.uint8) * 255
            for i in range(np.random.randint(5, 15)):
                x1, y1 = np.random.randint(0, image_size[0]), np.random.randint(0, image_size[1])
                x2, y2 = np.random.randint(0, image_size[0]), np.random.randint(0, image_size[1])
                cv2.line(img, (x1, y1), (x2, y2), (0, 0, 0), 2)
            
            # 处理图像
            request_start = time.time()
            try:
                result = detect_glass_flatness(img, save_intermediate=False)
                response_times.append(time.time() - request_start)
                processed_count += 1
            except Exception as e:
                error_count += 1
                print(f"错误: {e}")
            
            # 短暂休息，模拟真实负载
            time.sleep(0.1)
        
        monitor_thread.join()
        total_time = time.time() - start_time
        
        self.results['endurance_tests'].append({
            'duration_minutes': duration_minutes,
            'total_processed': processed_count,
            'error_count': error_count,
            'error_rate': error_count / (processed_count + error_count) * 100 if processed_count + error_count > 0 else 0,
            'avg_response_time': np.mean(response_times) if response_times else 0,
            'p95_response_time': np.percentile(response_times, 95) if response_times else 0,
            'p99_response_time': np.percentile(response_times, 99) if response_times else 0,
            'throughput': processed_count / total_time
        })
        
    def test_spike_load(self):
        """突发负载测试"""
        print("开始突发负载测试...")
        
        image_size = (1280, 720)
        normal_load = 5
        spike_load = 50
        duration_seconds = 30
        
        results = []
        
        # 正常负载阶段
        print("正常负载阶段...")
        for i in range(normal_load):
            img = np.ones((image_size[1], image_size[0], 3), dtype=np.uint8) * 255
            start = time.time()
            detect_glass_flatness(img, save_intermediate=False)
            results.append({
                'phase': 'normal',
                'timestamp': i,
                'response_time': time.time() - start
            })
            time.sleep(1)
        
        # 突发负载阶段
        print("突发负载阶段...")
        spike_threads = []
        spike_results = [None] * spike_load
        
        def process_spike(idx):
            img = np.ones((image_size[1], image_size[0], 3), dtype=np.uint8) * 255
            start = time.time()
            try:
                detect_glass_flatness(img, save_intermediate=False)
                spike_results[idx] = time.time() - start
            except Exception as e:
                spike_results[idx] = None
        
        # 同时启动所有请求
        for i in range(spike_load):
            thread = threading.Thread(target=process_spike, args=(i,))
            thread.start()
            spike_threads.append(thread)
        
        # 等待完成
        for thread in spike_threads:
            thread.join()
        
        # 恢复阶段
        print("恢复阶段...")
        for i in range(normal_load):
            img = np.ones((image_size[1], image_size[0], 3), dtype=np.uint8) * 255
            start = time.time()
            detect_glass_flatness(img, save_intermediate=False)
            results.append({
                'phase': 'recovery',
                'timestamp': normal_load + spike_load + i,
                'response_time': time.time() - start
            })
            time.sleep(1)
        
        # 分析结果
        spike_success = sum(1 for r in spike_results if r is not None)
        spike_response_times = [r for r in spike_results if r is not None]
        
        self.results['spike_tests'].append({
            'normal_load': normal_load,
            'spike_load': spike_load,
            'spike_success_rate': spike_success / spike_load * 100,
            'normal_avg_response': np.mean([r['response_time'] for r in results if r['phase'] == 'normal']),
            'spike_avg_response': np.mean(spike_response_times) if spike_response_times else 0,
            'recovery_avg_response': np.mean([r['response_time'] for r in results if r['phase'] == 'recovery']),
            'max_spike_response': np.max(spike_response_times) if spike_response_times else 0
        })
        
    def test_resource_limits(self):
        """资源限制测试"""
        print("开始资源限制测试...")
        
        # 测试不同大小的图像直到内存或时间限制
        test_sizes = [
            (640, 480),
            (1920, 1080),
            (3840, 2160),
            (7680, 4320),
            (15360, 8640)
        ]
        
        for size in test_sizes:
            print(f"测试图像尺寸: {size}")
            
            try:
                # 创建图像
                img = np.ones((size[1], size[0], 3), dtype=np.uint8) * 255
                
                # 记录资源使用
                process = psutil.Process()
                memory_before = process.memory_info().rss / 1024 / 1024
                
                # 设置超时
                start_time = time.time()
                timeout = 60  # 60秒超时
                
                # 处理图像
                result = detect_glass_flatness(img, save_intermediate=False)
                process_time = time.time() - start_time
                
                memory_after = process.memory_info().rss / 1024 / 1024
                
                self.results['resource_limit_tests'].append({
                    'image_size': f'{size[0]}x{size[1]}',
                    'pixels': size[0] * size[1],
                    'success': True,
                    'process_time': process_time,
                    'memory_used_mb': memory_after - memory_before,
                    'memory_per_megapixel': (memory_after - memory_before) / (size[0] * size[1] / 1000000)
                })
                
            except Exception as e:
                self.results['resource_limit_tests'].append({
                    'image_size': f'{size[0]}x{size[1]}',
                    'pixels': size[0] * size[1],
                    'success': False,
                    'error': str(e)
                })
                print(f"处理失败: {e}")
                break
                
    def generate_stress_report(self):
        """生成压力测试报告"""
        report = {
            'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'platform': sys.platform
            },
            'results': self.results
        }
        
        # 保存报告
        with open('test/test_reports/stress_test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
            
        # 生成可视化
        self.generate_stress_visualizations()
        
        return report
        
    def generate_stress_visualizations(self):
        """生成压力测试可视化"""
        plt.figure(figsize=(15, 10))
        
        # 负载测试结果
        if self.results['load_tests']:
            plt.subplot(2, 2, 1)
            loads = [t['concurrent_level'] for t in self.results['load_tests']]
            throughputs = [t['throughput'] for t in self.results['load_tests']]
            success_rates = [t['success_rate'] for t in self.results['load_tests']]
            
            ax1 = plt.gca()
            ax1.plot(loads, throughputs, 'b-o', label='吞吐量')
            ax1.set_xlabel('并发数')
            ax1.set_ylabel('吞吐量 (req/s)', color='b')
            ax1.tick_params(axis='y', labelcolor='b')
            
            ax2 = ax1.twinx()
            ax2.plot(loads, success_rates, 'r-o', label='成功率')
            ax2.set_ylabel('成功率 (%)', color='r')
            ax2.tick_params(axis='y', labelcolor='r')
            
            plt.title('负载测试结果')
            plt.grid(True)
        
        # 突发负载响应时间
        if self.results['spike_tests']:
            plt.subplot(2, 2, 2)
            test = self.results['spike_tests'][0]
            phases = ['正常', '突发', '恢复']
            response_times = [
                test['normal_avg_response'],
                test['spike_avg_response'],
                test['recovery_avg_response']
            ]
            
            plt.bar(phases, response_times, color=['green', 'red', 'blue'])
            plt.ylabel('平均响应时间 (秒)')
            plt.title('突发负载响应时间对比')
        
        # 资源限制测试
        if self.results['resource_limit_tests']:
            plt.subplot(2, 2, 3)
            successful_tests = [t for t in self.results['resource_limit_tests'] if t['success']]
            if successful_tests:
                pixels = [t['pixels']/1000000 for t in successful_tests]
                times = [t['process_time'] for t in successful_tests]
                
                plt.plot(pixels, times, 'o-')
                plt.xlabel('图像大小 (百万像素)')
                plt.ylabel('处理时间 (秒)')
                plt.title('大图像处理性能')
                plt.grid(True)
        
        # 持久性测试结果
        if self.results['endurance_tests']:
            plt.subplot(2, 2, 4)
            test = self.results['endurance_tests'][0]
            metrics = ['平均响应', 'P95响应', 'P99响应']
            values = [
                test['avg_response_time'],
                test['p95_response_time'],
                test['p99_response_time']
            ]
            
            plt.bar(metrics, values)
            plt.ylabel('响应时间 (秒)')
            plt.title(f'持久性测试响应时间分布 ({test["duration_minutes"]}分钟)')
        
        plt.tight_layout()
        plt.savefig('test/test_reports/stress_test_visualization.png', dpi=150)
        plt.close()
        
    def run_all_stress_tests(self):
        """运行所有压力测试"""
        print("开始运行压力测试套件...")
        
        self.test_load_capacity()
        self.test_spike_load()
        self.test_resource_limits()
        self.test_endurance(duration_minutes=2)  # 缩短为2分钟用于演示
        
        report = self.generate_stress_report()
        
        print("\n压力测试完成！")
        print(f"报告已保存至: test/test_reports/stress_test_report.json")
        print(f"可视化图表已保存至: test/test_reports/stress_test_visualization.png")
        
        return report


if __name__ == '__main__':
    stress_test = StressTest()
    stress_test.run_all_stress_tests()