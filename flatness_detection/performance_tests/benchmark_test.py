"""
基准性能测试脚本
用于测试单个请求的基准性能
"""

import requests
import time
import statistics
import json
from datetime import datetime
import concurrent.futures
import psutil
import os

class BenchmarkTest:
    def __init__(self):
        self.flatness_base_url = "http://localhost:8080"
        self.spalling_base_url = "http://localhost:9090"
        self.test_image_url = "http://110.42.214.164:9000/test/sample.jpg"
        self.test_username = "benchmark_user"
        
    def measure_request_time(self, func, *args, **kwargs):
        """测量单个请求的执行时间"""
        start_time = time.time()
        try:
            response = func(*args, **kwargs)
            end_time = time.time()
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": (end_time - start_time) * 1000,  # 转换为毫秒
                "response_size": len(response.content)
            }
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "error": str(e),
                "response_time": (end_time - start_time) * 1000
            }
    
    def test_flatness_detect(self):
        """测试平整度检测接口的基准性能"""
        print("\n=== 平整度检测接口基准测试 ===")
        
        data = {
            "url": self.test_image_url,
            "username": self.test_username
        }
        
        results = []
        for i in range(10):
            result = self.measure_request_time(
                requests.post,
                f"{self.flatness_base_url}/flatness/detect",
                json=data
            )
            results.append(result)
            print(f"请求 {i+1}: {result['response_time']:.2f}ms")
            time.sleep(1)  # 避免过于频繁的请求
        
        # 计算统计信息
        response_times = [r['response_time'] for r in results if r['success']]
        if response_times:
            print(f"\n统计信息:")
            print(f"平均响应时间: {statistics.mean(response_times):.2f}ms")
            print(f"最小响应时间: {min(response_times):.2f}ms")
            print(f"最大响应时间: {max(response_times):.2f}ms")
            print(f"标准差: {statistics.stdev(response_times):.2f}ms")
            print(f"成功率: {len(response_times)/len(results)*100:.1f}%")
        
        return results
    
    def test_spalling_classify(self):
        """测试爆裂检测分类接口的基准性能"""
        print("\n=== 爆裂检测分类接口基准测试 ===")
        
        data = {
            'url': self.test_image_url,
            'username': self.test_username
        }
        
        results = []
        for i in range(10):
            result = self.measure_request_time(
                requests.post,
                f"{self.spalling_base_url}/defect/classify",
                data=data
            )
            results.append(result)
            print(f"请求 {i+1}: {result['response_time']:.2f}ms")
            time.sleep(1)
        
        # 计算统计信息
        response_times = [r['response_time'] for r in results if r['success']]
        if response_times:
            print(f"\n统计信息:")
            print(f"平均响应时间: {statistics.mean(response_times):.2f}ms")
            print(f"最小响应时间: {min(response_times):.2f}ms")
            print(f"最大响应时间: {max(response_times):.2f}ms")
            print(f"标准差: {statistics.stdev(response_times):.2f}ms")
            print(f"成功率: {len(response_times)/len(results)*100:.1f}%")
        
        return results
    
    def test_concurrent_requests(self, num_concurrent=5):
        """测试并发请求性能"""
        print(f"\n=== 并发请求测试 (并发数: {num_concurrent}) ===")
        
        def make_flatness_request():
            data = {
                "url": self.test_image_url,
                "username": f"concurrent_user_{time.time()}"
            }
            return self.measure_request_time(
                requests.post,
                f"{self.flatness_base_url}/flatness/detect",
                json=data
            )
        
        # 使用线程池执行并发请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            start_time = time.time()
            futures = [executor.submit(make_flatness_request) for _ in range(num_concurrent)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            total_time = (time.time() - start_time) * 1000
        
        # 分析结果
        successful_requests = [r for r in results if r['success']]
        response_times = [r['response_time'] for r in successful_requests]
        
        print(f"\n并发测试结果:")
        print(f"总耗时: {total_time:.2f}ms")
        print(f"成功请求数: {len(successful_requests)}/{num_concurrent}")
        if response_times:
            print(f"平均响应时间: {statistics.mean(response_times):.2f}ms")
            print(f"最大响应时间: {max(response_times):.2f}ms")
        
        return results
    
    def monitor_system_resources(self, duration=10):
        """监控系统资源使用情况"""
        print(f"\n=== 系统资源监控 ({duration}秒) ===")
        
        cpu_usage = []
        memory_usage = []
        
        for i in range(duration):
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            cpu_usage.append(cpu_percent)
            memory_usage.append(memory_percent)
            
            print(f"时间 {i+1}s - CPU: {cpu_percent}%, 内存: {memory_percent}%")
        
        print(f"\n资源使用统计:")
        print(f"平均CPU使用率: {statistics.mean(cpu_usage):.1f}%")
        print(f"最大CPU使用率: {max(cpu_usage):.1f}%")
        print(f"平均内存使用率: {statistics.mean(memory_usage):.1f}%")
        print(f"最大内存使用率: {max(memory_usage):.1f}%")
        
        return {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage
        }
    
    def generate_report(self, results):
        """生成测试报告"""
        report = {
            "test_time": datetime.now().isoformat(),
            "test_results": results,
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "total_memory": psutil.virtual_memory().total / (1024**3),  # GB
                "python_version": os.sys.version
            }
        }
        
        # 保存报告
        with open('benchmark_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n测试报告已保存到 benchmark_report.json")

def main():
    print("开始基准性能测试...")
    
    benchmark = BenchmarkTest()
    
    # 检查服务是否可用
    try:
        requests.get(f"{benchmark.flatness_base_url}/test", timeout=5)
        print("✓ 平整度检测服务正常")
    except:
        print("✗ 平整度检测服务不可用")
        return
    
    try:
        requests.get(f"{benchmark.spalling_base_url}/test", timeout=5)
        print("✓ 爆裂检测服务正常")
    except:
        print("✗ 爆裂检测服务不可用")
        return
    
    # 执行测试
    results = {}
    
    # 1. 基准性能测试
    results['flatness_baseline'] = benchmark.test_flatness_detect()
    results['spalling_baseline'] = benchmark.test_spalling_classify()
    
    # 2. 并发测试
    results['concurrent_5'] = benchmark.test_concurrent_requests(5)
    results['concurrent_10'] = benchmark.test_concurrent_requests(10)
    
    # 3. 系统资源监控
    results['system_resources'] = benchmark.monitor_system_resources(10)
    
    # 生成报告
    benchmark.generate_report(results)
    
    print("\n基准测试完成!")

if __name__ == "__main__":
    main()